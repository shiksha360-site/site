package common

import (
	"io/ioutil"
	"math/rand"
	"shiksdk/types"
	"sort"

	"github.com/vmihailenco/msgpack/v5"
)

var boardCache []string

const letterBytes = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

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
