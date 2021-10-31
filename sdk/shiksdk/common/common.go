package common

import (
	"encoding/json"
	"io/ioutil"
	"math/rand"
	"net/smtp"
	"shiksdk/types"
	"sort"

	log "github.com/sirupsen/logrus"
	"github.com/vmihailenco/msgpack/v5"
)

var boardCache []string

const letterBytes = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

// smtp server configuration.
var smtpHost = "smtp.gmail.com"
var smtpPort = "587"
var smtpUsername string
var smtpPassword string

var currServer = "http://127.0.0.1"

func SetupEmailCreds() {
	smtpCreds, err := ioutil.ReadFile("secrets/email_creds.json")
	if err != nil {
		panic(err)
	}
	var smtpData types.SMTPCredsJSON
	err = json.Unmarshal(smtpCreds, &smtpData)
	if err != nil {
		panic(err)
	}
	smtpUsername = smtpData.Username
	smtpPassword = smtpData.Password
}

func SendRecoveryEmail(userId string, email string, resetToken string) {
	var emails []string
	emails = append(emails, email)
	auth := smtp.PlainAuth("", smtpUsername, smtpPassword, smtpHost)
	msgContent := "<h1>Hi there!</h1><br/>We have noticed an attempted account recovery/password reset. If this was you, please go <a href='" + currServer + "/recovery_stage2.html?user_id=" + userId + "&token=" + resetToken + "'>here</a> to reset your shiksha360 password. If this wasn't you, use this link to reset your password immediately! This link will expire in 5 minutes"

	msg := "From: " + smtpUsername + "\n" + "To: " + email + "\n" + "Content-Type: text/html\nSubject: Account Recovery Request\n\n" + msgContent

	err := smtp.SendMail(smtpHost+":"+smtpPort, auth, smtpUsername, emails, []byte(msg))
	if err != nil {
		log.Error(err)
	}
}

func GetCmdKeys(cmdMap map[string]types.Command) []string {
	keys := make([]string, 0, len(cmdMap))
	for k := range cmdMap {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func RandStringBytes(n int) string {
	b := make([]byte, n)
	for i := range b {
		b[i] = letterBytes[rand.Intn(len(letterBytes))]
	}
	return string(b)
}

func IsInList(list []string, a string) bool {
	for _, b := range list {
		if b == a {
			return true
		}
	}
	return false
}

func GetBoardList() []string {
	if boardCache != nil {
		return boardCache
	}
	boards, err := ioutil.ReadFile("data/build/keystone/boards.lynx")

	if err != nil {
		return nil
	}

	var boardList []string

	err = msgpack.Unmarshal(boards, &boardList)

	if err != nil {
		return nil
	}

	boardCache = boardList
	return boardList
}
