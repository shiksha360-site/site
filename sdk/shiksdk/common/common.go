package common

import (
	"shiksdk/types"
	"sort"
)

// Event channel controls all inter-server events
var EventChannel = make(chan []byte)

func GetCmdKeys(cmdMap map[string]types.Command) []string {
	keys := make([]string, 0, len(cmdMap))
	for k := range cmdMap {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}
