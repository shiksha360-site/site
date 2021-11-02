// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package server

import (
	"encoding/json"
	"regexp"
	"shiksdk/common"
	"shiksdk/types"
	"strconv"
	"strings"
	"time"

	"crypto/subtle"
	"errors"

	"github.com/andskur/argon2-hashing"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
	ginlogrus "github.com/toorop/gin-logrus"
)

var logger = log.New()
var errAuthFailed = errors.New("authentication_failed")

func apiReturn(done bool, reason interface{}, context interface{}) gin.H {
	if reason == "EOF" {
		reason = "Request body required"
	}

	if reason == "" {
		reason = nil
	}

	if context == nil {
		return gin.H{
			"done":   done,
			"reason": reason,
		}
	} else {
		return gin.H{
			"done":   done,
			"reason": reason,
			"ctx":    context,
		}
	}
}

func prefValidate(data types.UserPreferences) gin.H {
	boards := common.GetBoardList()

	if boards == nil {
		return apiReturn(false, "Could not fetch board information", nil)
	}

	if !common.IsInList(boards, data.Board) {
		return apiReturn(false, "Invalid Board", nil)
	}
	return nil
}

func authHandle(db *pgxpool.Pool, c *gin.Context, userId string) error {
	var auth types.AuthHeader
	if err := c.ShouldBindHeader(&auth); err != nil {
		return err
	}

	var tokenCheck pgtype.Text

	db.QueryRow(ctx, "SELECT token FROM users WHERE user_id = $1", userId).Scan(&tokenCheck)

	// Basic timing checks. This is likely not superbly robust but should be enough for our use case and purposes
	token := []byte(tokenCheck.String)

	check := subtle.ConstantTimeCompare(token, []byte(auth.Authorization))

	if check == 1 && tokenCheck.Status == pgtype.Present {
		return nil
	}

	return errAuthFailed
}

func StartServer(prefix string, dirname string, db *pgxpool.Pool, rdb *redis.Client) {
	// Compile alphanumeric regex
	alphanumeric, err := regexp.Compile("^[A-Za-z0-9][A-Za-z0-9_-]*$")

	if err != nil {
		panic(err)
	}

	hub := newHub(db, rdb)
	go hub.run()

	//gin.SetMode(gin.ReleaseMode)

	r := gin.New()
	r.Use(ginlogrus.Logger(logger), gin.Recovery())

	router := r.Group(prefix)

	router.GET("/", func(c *gin.Context) {
		c.JSON(200, apiReturn(true, "Pong!", nil))
	})
	router.POST("/register", func(c *gin.Context) {
		var data types.Register
		err := c.ShouldBindJSON(&data)
		if err != nil {
			c.JSON(422, apiReturn(false, err.Error(), nil))
			return
		}

		if !alphanumeric.MatchString(data.Username) {
			c.JSON(400, apiReturn(false, "Invalid username. Usernames may only contain letters, numbers, hyphens and underscores!", nil))
			return
		}
		if data.Email != "" {
			if !strings.Contains(data.Email, "@") || !strings.Contains(data.Email, ".") {
				c.JSON(400, apiReturn(false, "The email address you provided was not a well formed email address", nil))
				return
			}
		}

		data.Username = strings.ToLower(data.Username)
		data.Email = strings.ToLower(data.Email)

		prefCheck := prefValidate(data.Preferences)

		if prefCheck != nil {
			c.JSON(400, prefCheck)
			return
		}

		var userIdCheck pgtype.Text

		if data.Email != "" {
			db.QueryRow(ctx, "SELECT user_id::text FROM users WHERE username = $1 OR email = $2", data.Username, data.Email).Scan(&userIdCheck)
		} else {
			db.QueryRow(ctx, "SELECT user_id::text FROM users WHERE username = $1", data.Username).Scan(&userIdCheck)
		}

		if userIdCheck.Status == pgtype.Present {
			c.JSON(400, apiReturn(false, "Username or email already taken!", nil))
			return
		}

		// Argon2 hash the password
		hash, err := argon2.GenerateFromPassword([]byte(data.Password), argon2.DefaultParams)
		if err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		preferences, err := json.Marshal(data.Preferences)

		if err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		token := common.RandStringBytes(193)

		var userId pgtype.Text

		err = db.QueryRow(ctx, "INSERT INTO users (username, pass, token, email, preferences) VALUES ($1, $2, $3, $4, $5) RETURNING user_id::text", data.Username, string(hash), token, data.Email, string(preferences)).Scan(&userId)

		if err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		c.JSON(206, apiReturn(true, nil, gin.H{"user_id": userId.String, "token": token, "preferences": data.Preferences}))
	})

	router.POST("/login", func(c *gin.Context) {
		var data types.Login
		err := c.ShouldBindJSON(&data)
		if err != nil {
			c.JSON(422, apiReturn(false, err.Error(), nil))
			return
		}

		// Either username or email needed
		if data.Username != "" && data.Email != "" {
			c.JSON(400, apiReturn(false, "Only username OR email may be specified", nil))
			return
		} else if data.Username == "" && data.Email == "" {
			c.JSON(400, apiReturn(false, "One of username OR email is requirred", nil))
			return
		}

		data.Username = strings.ToLower(data.Username)
		data.Email = strings.ToLower(data.Email)

		// Get all fields
		var userId pgtype.Text
		var token pgtype.Text
		var passHash pgtype.Text
		var loginAttempts pgtype.Int4
		var preferences pgtype.JSONB

		if data.Username != "" {
			err = db.QueryRow(ctx, "SELECT user_id::text, pass, token, login_attempts, preferences FROM users WHERE username = $1", data.Username).Scan(&userId, &passHash, &token, &loginAttempts, &preferences)
			if err != nil {
				log.Warn(err)
				c.JSON(400, apiReturn(false, "Incorrect username", nil))
				return
			}
		} else if data.Email != "" {
			err = db.QueryRow(ctx, "SELECT user_id::text, pass, token, login_attempts, preferences::text FROM users WHERE email = $1", data.Email).Scan(&userId, &passHash, &token, &loginAttempts, &preferences)
			if err != nil {
				c.JSON(400, apiReturn(false, "Incorrect email address", nil))
				return
			}
		}

		// Validate credentials and password using argon2
		if userId.Status != pgtype.Present {
			c.JSON(400, apiReturn(false, "Incorrect username", nil))
			return
		} else if loginAttempts.Int > 5 {
			db.Exec(ctx, "UPDATE users SET login_attempts = login_attempts + 1 WHERE user_id = $1", userId.String)
			c.JSON(400, apiReturn(false, "Maximum amount of login attempts exceeded ("+strconv.FormatInt(int64(loginAttempts.Int), 10)+")", nil))
			return
		}
		err = argon2.CompareHashAndPassword([]byte(passHash.String), []byte(data.Password))
		if err != nil {
			db.Exec(ctx, "UPDATE users SET login_attempts = login_attempts + 1 WHERE user_id = $1", userId.String)
			c.JSON(400, apiReturn(false, "Incorrect password", nil))
			return
		}
		go db.Exec(ctx, "UPDATE users SET login_attempts = 0 WHERE user_id = $1", userId.String)

		c.JSON(206, apiReturn(true, nil, gin.H{"user_id": userId.String, "token": token.String, "preferences": preferences}))
	})

	router.POST("/account/recovery", func(c *gin.Context) {
		var data types.AccountRecovery
		err := c.ShouldBindJSON(&data)
		if err != nil {
			c.JSON(422, apiReturn(false, err.Error(), nil))
			return
		}

		if data.Username != "" && data.Email != "" {
			c.JSON(400, apiReturn(false, "Only username OR email may be specified", nil))
			return
		} else if data.Username == "" && data.Email == "" {
			c.JSON(400, apiReturn(false, "One of username OR email is requirred", nil))
			return
		}

		data.Username = strings.ToLower(data.Username)
		data.Email = strings.ToLower(data.Email)

		// Get the user id (and email) if needed
		var userId pgtype.Text
		var email string

		if data.Username != "" {
			var emailDb pgtype.Text
			err := db.QueryRow(ctx, "SELECT user_id::text, email FROM users WHERE username = $1", data.Username).Scan(&userId, &emailDb)
			if err != nil || userId.Status != pgtype.Present {
				c.JSON(400, apiReturn(false, "Username does not exist!", nil))
				return
			}
			if emailDb.Status == pgtype.Null || emailDb.String == "" {
				c.JSON(400, apiReturn(false, "This user account does not have an associated recovery email address... Please click <a href='https://github.com/shiksha360-site/site/issues/new/choose'>here</a> and choose 'Account Recovery'", nil))
				return
			}
			email = emailDb.String
		} else if data.Email != "" {
			err := db.QueryRow(ctx, "SELECT user_id::text FROM users WHERE email = $1", data.Email).Scan(&userId)
			if err != nil || userId.Status != pgtype.Present {
				c.JSON(400, apiReturn(false, "Email is not registered!", nil))
				return
			}
			email = data.Email
		}

		// Send the reset email
		resetToken := common.RandStringBytes(169)
		go rdb.Set(ctx, "recovery-"+resetToken, userId.String, 5*time.Minute)

		go common.SendRecoveryEmail(userId.String, email, resetToken)

		c.JSON(200, apiReturn(true, "Sent recovery email. Check your spam folder if you didn't recieve it within a few minutes", nil))
	})

	// HEAD /account/recovery?user_id=USERID&token=TOKEN -> Checks whether or not a user_id, token combo is valid
	router.HEAD("/account/recovery", func(c *gin.Context) {
		userId := c.Query("user_id")
		token := c.Query("token")

		if token == "" || userId == "" {
			c.Status(422)
			return
		}

		data := rdb.Get(ctx, "recovery-"+token).Val()
		log.Info(data, userId)
		if data == userId {
			c.Status(200)
			return
		}
		c.Status(400)
	})

	router.PATCH("/preferences", func(c *gin.Context) {
		var data types.ModifyUserPreferences
		err := c.ShouldBindJSON(&data)
		if err != nil {
			c.JSON(422, apiReturn(false, err.Error(), nil))
			return
		}

		err = authHandle(db, c, data.UserId)

		if err != nil {
			c.JSON(401, apiReturn(false, err.Error(), nil))
			return
		}

		prefCheck := prefValidate(data.Preferences)

		if prefCheck != nil {
			c.JSON(400, prefCheck)
			return
		}

		preferences, err := json.Marshal(data.Preferences)

		if err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		go db.Exec(ctx, "UPDATE users SET preferences = $1 WHERE user_id = $2", string(preferences), data.UserId)

		c.JSON(200, apiReturn(true, nil, nil))
	})

	router.PATCH("/videos/track", func(c *gin.Context) {
		var data types.VideoTracker
		err := c.ShouldBindJSON(&data)
		if err != nil {
			c.JSON(422, apiReturn(false, err.Error(), nil))
			return
		}

		err = authHandle(db, c, data.UserId)

		if err != nil {
			c.JSON(401, apiReturn(false, err.Error(), nil))
			return
		}

		var videoPreferencesDb pgtype.JSONB
		var resAuthor pgtype.Text

		db.QueryRow(ctx, "SELECT video_preferences FROM users WHERE user_id = $1", data.UserId).Scan(&videoPreferencesDb)
		db.QueryRow(ctx, "SELECT resource_author FROM topic_resources WHERE resource_id = $1", data.ResourceId).Scan(&resAuthor)

		if resAuthor.Status != pgtype.Present {
			c.JSON(404, apiReturn(false, "Resource Not Found", nil))
			return
		}

		var videoPreferences map[string]types.VideoPreferences
		if videoPreferencesDb.Status == pgtype.Present {
			err = videoPreferencesDb.AssignTo(&videoPreferences)

			if err != nil {
				c.JSON(400, apiReturn(false, err.Error(), nil))
				return
			}
		}

		resPref := videoPreferences[data.ResourceId]

		if data.IFrame {
			resPref.Views += 1
			if data.FullyWatched {
				resPref.TimesFullyWatched += 1
			}
		} else {
			// TODO: Do all the other video tracking code here
			if resPref.Progress < data.Duration {
				resPref.Progress = data.Duration
			}
		}

		resPref.ResourceAuthor = resAuthor.String

		videoPreferences[data.ResourceId] = resPref

		pgDat, err := json.Marshal(videoPreferences)

		if err != nil {
			c.JSON(400, apiReturn(false, err.Error(), nil))
			return
		}

		go db.Exec(ctx, "UPDATE users SET video_preferences = $1 WHERE user_id = $2", pgDat, data.UserId)

		c.JSON(200, apiReturn(true, nil, nil))
	})

	router.GET("/ws", func(c *gin.Context) {
		serveWs(hub, c.Writer, c.Request)
	})

	r.RunUnix(dirname + "/shiksha.sock")
}
