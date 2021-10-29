# Ported from https://github.com/Fates-List/FatesList/blob/main/modules/core/error.py

from http import HTTPStatus
from fastapi.responses import ORJSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from lynxfall.utils.fastapi import api_error
import inspect
import traceback
import uuid
import time

def etrace(ex):
     return "".join(traceback.format_exception(ex)) # COMPAT: Python 3.10 only

class WebError():
    @staticmethod
    async def error_handler(request, exc, log: bool = True):

        error_id = str(uuid.uuid4())
        curr_time = time.time()

        try:
            # All status codes other than 500 and 422
            status_code = exc.status_code 
        
        except Exception: 
            # 500 and 422 do not have status codes and need special handling
            if isinstance(exc, RequestValidationError): 
                status_code = 422
            
            else: 
                status_code = 500
        
        path = str(request.url.path)
        
        code_str = HTTPStatus(status_code).phrase
        api = path.startswith("/api/") and not request.app.state.is_internal
        if status_code == 500:
            # Log the error            
            if api:
                return api_error(
                    "Internal Server Error", 
                    error_id=error_id, 
                    status_code=500,
                    traceback=etrace(exc),
                    headers={"FL-Error-ID": error_id}
                )
            
            tb_full = "".join(traceback.format_exception(exc))

            if not request.app.state.is_internal:
                errmsg = inspect.cleandoc(f"""
                We've had a slight issue we are looking into what happened<br/><br/>
                
                Error ID: {error_id}<br/><br/>
                Please send the below traceback if asked:<br/><br/>
                <pre>{tb_full}</pre>
                Time When Error Happened: {curr_time}<br/>""")
            else:
                errmsg = tb_full

            return HTMLResponse(errmsg, status_code=status_code, headers={"FL-Error-ID": error_id})

        #if not api:            
        #    return await templates.e(request, code_str, status_code)

        # API route handling
        if status_code != 422:
            # Normal handling
            return ORJSONResponse({"done": False, "reason": exc.detail}, status_code=status_code)
        else:
            errors = exc.errors()
            errors_fixed = []
            for error in errors:
                if error["type"] == "type_error.enum":
                    ev = [{"name": type(enum).__name__, "accepted": enum.value, "doc": enum.__doc__} for enum in error["ctx"]["enum_values"]]
                    error["ctx"]["enum"] = ev
                    del error["ctx"]["enum_values"]
                errors_fixed.append(error)
            return ORJSONResponse({"done": False, "reason": "Invalid fields present", "ctx": errors_fixed}, status_code=422)
