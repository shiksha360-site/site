# Ported from https://github.com/Fates-List/FatesList/blob/main/modules/core/system.py

from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger
from http import HTTPStatus
import uuid
import datetime
from lynxfall.utils.fastapi import api_versioner
import time
import os

class KalanRequestHandler(BaseHTTPMiddleware):
    """Request Handler for Fates List ported to Kalam Academy/Infilearn"""
    def __init__(self, app, *, exc_handler, api_ver):
        super().__init__(app)
        self.exc_handler = exc_handler
        self.api_ver = api_ver
        self.cwd = os.getcwd()
        app.add_exception_handler(Exception, exc_handler)
        
        # Methods that should be allowed by CORS
        self.cors_allowed = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"
    
        # Default response
        self.default_res = HTMLResponse(
            "Something happened!", 
            status_code=500
        ) 
    
    @staticmethod
    def _log_req(path, request, response):
        """Logs HTTP requests to console (and file)"""
        code = response.status_code
        phrase = HTTPStatus(response.status_code).phrase
        query_str_raw = request.scope["query_string"]

        if query_str_raw:
            query_str = f'?{query_str_raw.decode("utf-8")}'
        else:
            query_str = ""

        if request.app.state.gunicorn:    
            logger.info(
                f"{request.method} {path}{query_str} | {code} {phrase}"
            )
        
    async def dispatch(self, request, call_next):
        """Run _dispatch, if that fails, log error and do exc handler"""
        # Ensure we are always in cwd
        if os.getcwd() != self.cwd and not request.query_params.get("internal_http_call", False):
            os.chdir(self.cwd)

        request.state.error_id = str(uuid.uuid4())
        request.state.curr_time = str(datetime.datetime.now())
        path = request.scope["path"]
        
        if not request.app.state.ipc_up:
            # This middleware does not apply
            return await call_next(request)

        try:
            res = await self._dispatcher(path, request, call_next)
        except BaseException as exc:  # pylint: disable=broad-except
            #logger.exception("Site Error Occurred") 
            res = await self.exc_handler(request, exc, log=True)
        
        self._log_req(path, request, res)
        return res if res else self.default_res
    
    async def _dispatcher(self, path, request, call_next):
        """Actual middleware"""        
        logger.trace(request.headers.get("X-Forwarded-For"))
                
        # These are checks path should not start with
        is_api = path.startswith("/api")
        request.scope["path"] = path
        
        if is_api:
            # Handle /api as /api/vX excluding docs + pinned requests
            request.scope, api_ver = api_versioner(request, self.api_ver)
    
        start_time = time.time()
        
        # Process request with retry
        try:
            response = await call_next(request)
        except BaseException as exc:  # pylint: disable=broad-except
            #logger.exception("Site Error Occurred")
            response = await self.exc_handler(request, exc)

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)

        if is_api:
            response.headers["X-API-Version"] = api_ver
    
        # Fuck CORS by force setting headers with proper origin
        origin = request.headers.get('Origin')

        # Make commonly repepated headers shorter
        acac = "Access-Control-Allow-Credentials"
        acao = "Access-Control-Allow-Origin"
        acam = "Access-Control-Allow-Methods"

        response.headers[acao] = origin if origin else "*"
        
        if is_api and origin:
            response.headers[acac] = "true"
        else:
            response.headers[acac] = "false"
        
        response.headers[acam] = self.cors_allowed
        if response.status_code == 405:
            if request.method == "OPTIONS" and is_api:
                response.status_code = 204
                response.headers["Allow"] = self.cors_allowed

        return response