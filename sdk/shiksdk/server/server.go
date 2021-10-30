// Based on https://github.com/gorilla/websocket/blob/master/examples/chat/main.go

// Copyright 2013 The Gorilla WebSocket Authors. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

package server

import (
	"github.com/gin-gonic/gin"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
	ginlogrus "github.com/toorop/gin-logrus"
)

var logger = log.New()

func apiReturnSimple(done bool, reason string) gin.H {
	if reason == "" {
		return gin.H{
			"done":   done,
			"reason": nil,
		}
	} else {
		return gin.H{
			"done":   done,
			"reason": reason,
		}
	}
}

func StartServer(prefix string, dirname string, db *pgxpool.Pool, rdb *redis.Client) {
	hub := newHub(db, rdb)
	go hub.run()

	r := gin.New()
	r.Use(ginlogrus.Logger(logger), gin.Recovery())

	router := r.Group(prefix)

	router.GET("/", func(c *gin.Context) {
		c.JSON(200, apiReturnSimple(true, "Pong!"))
	})
	router.GET("/ws", func(c *gin.Context) {
		serveWs(hub, c.Writer, c.Request)
	})

	r.RunUnix(dirname + "/shiksha.sock")
}
