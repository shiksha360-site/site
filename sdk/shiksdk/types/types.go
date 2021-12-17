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

type WebsocketClientPayloadData struct {
	ContentType string      `json:"content-type"`
	Content     string      `json:"content"`
	Extra       interface{} `json:"extra,omitempty"`
}

// WebsocketClientPayload is a payload that is sent by a client
type WebsocketClientPayload struct {
	Code      string                     `json:"code"`
	Timestamp float64                    `json:"ts"`
	Data      WebsocketClientPayloadData `json:"data"`
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
	Board string `json:"board" binding:"required"`                          // The board must be manually validated for now using common.GetBoardList
}

type ModifyUserPreferences struct {
	UserId      string          `json:"user_id" binding:"required"` // Required field. This is the user id to track
	Preferences UserPreferences `json:"preferences"`                // The user preferences (grade and board) of a user
}

type Register struct {
	Username    string          `json:"username"`                    // The username of the new account. Either username or email must be present. It is up to the client to decide this
	Email       string          `json:"email"`                       // The email of the new account. Either username or email must be present. It is up to the client to decide this
	Password    string          `json:"password" binding:"required"` // The password of the new account.
	Preferences UserPreferences `json:"preferences"`                 // The user preferences (grade and board) of a user
}

type Login struct {
	Username string `json:"username"`                    // The username of the account. Either username or email must be present. It is up to the client to decide this
	Email    string `json:"email"`                       // The username of the account. Either username or email must be present. It is up to the client to decide this
	Password string `json:"password" binding:"required"` // The password of the new account.
}

type AccountRecovery struct {
	Username string `json:"username"` // The username of the account. Either username or email must be present. It is up to the client to decide this
	Email    string `json:"email"`    // The username of the account. Either username or email must be present. It is up to the client to decide this
}

type RecoverPass struct {
	Password string `json:"password" binding:"required"`
}

type VideoTracker struct {
	UserId       string  `json:"user_id" binding:"required"`     // Required field. This is the user id to track
	ResourceId   string  `json:"resource_id" binding:"required"` // Required field. This is the resource id to track
	Duration     float32 `json:"duration"`                       // The duration the user has watched the video for. The duration is currently only updated in the database after it has exceeded the last recorded duration
	State        int     `json:"state"`                          // Current playyer state (not used right now, but could be used to determine how long people watch each video before stopping). If a user spends a long time watching one video but pauses another after just a few minutes, then we can give preference to the other video)
	IFrame       bool    `json:"iframe"`                         // Whether this is a track event for opening a iframe or not
	FullyWatched bool    `json:"fully_watched"`                  // This is set to true once a video is fully watched
}

type AuthHeader struct {
	Authorization string `header:"Authorization" binding:"required"` // Authorization header to authorize possibly harmful/user-initiated action
}

type VideoPreferences struct {
	Views             int     `json:"views"`           // The amount of times a user has clicked on a possibly interesting video. This along with TimesFullyWatched are going to be used in personalization
	Progress          float32 `json:"progress"`        // Equivalent to VideoTracker.Duration: The duration the user has watched the video for. The duration is currently only updated in the database after it has exceeded the last recorded duration
	Rating            float32 `json:"rating"`          // The rating a user has given to a video if we ever add video rating
	Review            string  `json:"review"`          // The reviews a user has given to a video if we ever add video reviews
	TimesFullyWatched int     `json:"times_watched"`   // The total amount of times a user has fully watched a video. Unlike views, this only counts videos that have been watched till the end (even if they did not begin at the beginning)
	ResourceAuthor    string  `json:"resource_author"` // The author of the resource. Just there for caching to speed backend stuff up if needed
}
