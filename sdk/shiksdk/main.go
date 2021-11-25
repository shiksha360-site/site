package main

import (
	"context"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"shiksdk/common"
	"shiksdk/server"
	"shiksdk/types"
	"syscall"
	"time"

	"github.com/go-redis/redis/v8"
	"github.com/jackc/pgx/v4/pgxpool"
	log "github.com/sirupsen/logrus"
)

var (
	dirname   string
	db        *pgxpool.Pool
	rdb       *redis.Client
	blockExit bool = false // Whether or not shutdown should be blocked to allow services to cleanup (uvicorn needs this)
)

var sigs = make(chan os.Signal, 1)

var commands = make(map[string]types.Command)

func init() {
	lvl, ok := os.LookupEnv("LOG_LEVEL")
	if !ok {
		lvl = "debug"
	}
	ll, err := log.ParseLevel(lvl)
	if err != nil {
		ll = log.DebugLevel
	}
	log.SetLevel(ll)

	dirname, err = os.UserHomeDir()
	if err != nil {
		log.Fatal(err)
		return
	}

	err = os.Chdir(dirname + "/site")

	if err != nil {
		panic(err)
	}

	// Populate command list
	commands["devserver"] = types.Command{
		Description: "Run the internal api",
		Handler: func(cmd []string) {
			log.Info("Running python3.10 sdk/_devserver.py")
			blockExit = true
			os.Setenv("_DEV", "1")

			devserver := exec.Command(dirname+"/venv/bin/python3.10", "sdk/_devserver.py")
			devserver.Env = os.Environ()
			devserver.Stdout = os.Stdout

			// https://stackoverflow.com/questions/30993717/how-can-i-redirect-the-stdout-and-stderr-of-a-command-to-both-the-console-and-a

			// Logging capability
			f, err := os.OpenFile("devserver.log", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
			if err != nil {
				log.Fatalf("Error opening file: %v", err)
			}
			defer f.Close()
			mwriter := io.MultiWriter(f, os.Stdout)

			devserver.Stderr = mwriter

			if err := devserver.Start(); err != nil {
				log.Fatal(err)
				return
			}

			devserver.Wait()
		},
	}

	commands["mainserver"] = types.Command{
		Description: "Runs the main server for Shiksha360",
		Handler: func(cmd []string) {
			dbSetupAndCleanup()

			os.Remove(dirname + "/shiksha.sock")

			// TODO: CHANGE THIS IN PROD
			prefix := "/api"

			// Setup smtp
			common.SetupEmailCreds()

			// Start server
			server.StartServer(prefix, dirname, db, rdb)
		},
	}

}

func dbSetupAndCleanup() {
	var err error
	db, err = pgxpool.Connect(context.Background(), "")
	if err != nil {
		panic(err)
	}

	rdb = redis.NewClient(&redis.Options{
		Addr:     "localhost:9282",
		Password: "",
		DB:       0,
	})
}

func main() {
	if len(os.Args) < 2 {
		log.Error("Command must be one of: ", common.GetCmdKeys(commands))
		os.Exit(-1)
	}

	if val, ok := commands[os.Args[1]]; ok {
		go val.Handler(os.Args[1:])
	} else {
		log.Fatal("Invalid command! Command must be one of: ", common.GetCmdKeys(commands))
		return
	}

	// Channel for signal handling
	signal.Notify(sigs,
		syscall.SIGINT,
		syscall.SIGQUIT)

	s := <-sigs

	// Give one second for all commands to reorient unless we have a user defined signal 1 or 2
	if s != syscall.SIGUSR1 {
		if blockExit {
			time.Sleep(1 * time.Second)
		}
		log.Info("Going to exit gracefully due to signal", s, "\n")
	}

	if db != nil {
		db.Close()
	}
	if rdb != nil {
		rdb.Close()
	}
	os.Exit(0)
}
