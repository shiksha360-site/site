package types

type Command struct {
	Description string             // Internal description
	Handler     func(cmd []string) // Function associated with the command
}

type SMTPCredsJSON struct {
	Username string `json:"username"`
	Password string `json:"password"`
}

type WebsocketIdentifyPayload struct {
	ID       string `json:"id"`        // ID
	Token    string `json:"token"`     // Token
	SendAll  bool   `json:"send_all"`  // Whether to send all prior messages, may dramatically increase startup time
	SendNone bool   `json:"send_none"` // Send none status
}

type WebsocketPayload struct {
	Code              string  `json:"code"`
	Detail            string  `json:"detail"`
	Timestamp         float64 `json:"ts"`
	RequestsRemaining int     `json:"requests_remaining"`
	Control           bool    `json:"control"`
}

type WebsocketCloseCode struct {
	Code        int
	Description string
}

var (
	InvalidConn   = WebsocketCloseCode{Code: 4000, Description: "Invalid connection, try again"}
	InvalidAuth   = WebsocketCloseCode{Code: 4004, Description: "Invalid authentication, try again"}
	Ratelimited   = WebsocketCloseCode{Code: 4012, Description: "Ratelimited"}
	InternalError = WebsocketCloseCode{Code: 4500, Description: "Internal Server Error, try reconnecting?"}
)

type UserPreferences struct {
	Grade int    `json:"grade" binding:"required,oneof=5 6 7 8 9 10 11 12"` // Add new grades here
	Board string `json:"board" binding:"required"`
}

type Register struct {
	Username    string          `json:"username" binding:"required"`
	Password    string          `json:"password" binding:"required"`
	Email       string          `json:"email"`
	Preferences UserPreferences `json:"preferences"`
}

type Login struct {
	Username string `json:"username"`
	Email    string `json:"email"`
	Password string `json:"password" binding:"required"`
}

type AccountRecovery struct {
	Username string `json:"username"`
	Email    string `json:"email"`
}

type VideoTracker struct {
	UserId    string `json:"user_id" binding:"required"`
	VideoId   string `json:"video_id" binding:"required"`
	Duration  int    `json:"duration" binding:"required"`
	IsPlaying bool   `json:"is_playing" binding:"required"`
}

type AuthHeader struct {
	Authorization string `header:"Authorization" binding:"required"`
}
