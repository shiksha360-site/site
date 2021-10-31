// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package server

import (
	"encoding/json"
	"shiksdk/common"
	"shiksdk/types"
	"strconv"
	"time"

	"github.com/andskur/argon2-hashing"
	"github.com/gin-gonic/gin"
	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgtype"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
	ginlogrus "github.com/toorop/gin-logrus"
)

var logger = log.New()

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

func StartServer(prefix string, dirname string, db *pgxpool.Pool, rdb *redis.Client) {
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

		boards := common.GetBoardList()

		if boards == nil {
			c.JSON(400, apiReturn(false, "Could not fetch board information", nil))
			return
		}

		if !common.IsInList(boards, data.Preferences.Board) {
			c.JSON(400, apiReturn(false, "Invalid Board", nil))
			return
		}

		var userIdCheck pgtype.Text

		db.QueryRow(ctx, "SELECT user_id::text FROM users WHERE username = $1", data.Username).Scan(&userIdCheck)

		if userIdCheck.Status == pgtype.Present {
			c.JSON(400, apiReturn(false, "Username already taken!", nil))
			return
		}

		// Argon2 hash the password
		hash, err := argon2.GenerateFromPassword([]byte(data.Password), argon2.DefaultParams)
		if err != nil {
			c.JSON(409, apiReturn(false, err.Error(), nil))
			return
		}

		preferences, err := json.Marshal(data.Preferences)

		if err != nil {
			c.JSON(409, apiReturn(false, err.Error(), nil))
			return
		}

		token := common.RandStringBytes(193)

		var userId pgtype.Text

		err = db.QueryRow(ctx, "INSERT INTO users (username, pass, token, preferences) VALUES ($1, $2, $3, $4) RETURNING user_id::text", data.Username, string(hash), token, string(preferences)).Scan(&userId)

		if err != nil {
			c.JSON(409, apiReturn(false, err.Error(), nil))
			return
		}

		c.JSON(206, apiReturn(true, nil, gin.H{"user_id": userId.String, "token": token}))
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

		// Get all fields
		var userId pgtype.Text
		var token pgtype.Text
		var passHash pgtype.Text
		var loginAttempts pgtype.Int4
		var preferences pgtype.Text

		if data.Username != "" {
			err = db.QueryRow(ctx, "SELECT user_id::text, pass, token, login_attempts, preferences::text FROM users WHERE username = $1", data.Username).Scan(&userId, &passHash, &token, &loginAttempts, &preferences)
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
		db.Exec(ctx, "UPDATE users SET login_attempts = 0 WHERE user_id = $1", userId.String)
		c.JSON(206, apiReturn(true, nil, gin.H{"user_id": userId.String, "token": token.String, "preferences": preferences.String}))
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
			if emailDb.Status == pgtype.Null {
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
		rdb.Set(ctx, "recovery-"+resetToken, userId.String, 5*time.Minute)

		common.SendRecoveryEmail(userId.String, email, resetToken)

		c.JSON(200, apiReturn(true, "Sent recovery email. Check your spam folder if you didn't recieve it", nil))
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

	router.GET("/ws", func(c *gin.Context) {
		serveWs(hub, c.Writer, c.Request)
	})

	r.RunUnix(dirname + "/shiksha.sock")
}
