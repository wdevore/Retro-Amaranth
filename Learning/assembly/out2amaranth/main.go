package main

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// ---------------------------------------------------------
// input file format is:
// @00000000 50500513
// @00000001 000015B7
// @00000002 A0A58593
// @00000003 00B54633
// @00000004 00100073
//
// output is:
// self.instructions.append(0x50500513)
// self.instructions.append(0x000015B7)
// self.instructions.append(0xA0A58593)
// self.instructions.append(0x00B54633)
// self.instructions.append(0x00100073)

// ---------------------------------------------------------

func main() {
	args := os.Args[1:]

	//
	// Search for the "_start" entry point. The address we find
	// is what we subtract from all instruction addresses.
	fileName := args[0]
	outFileName := args[1]

	// Open our jsonFile
	dumpfile, err := os.Open(fileName)
	if err != nil {
		fmt.Println(err)
		os.Exit(-1)
	}

	// defer the closing of our jsonFile so that we can parse it later on
	defer dumpfile.Close()

	//fmt.Printf("Successfully Opened `%s`\n", fileName)

	scanner := bufio.NewScanner(dumpfile)

	firmware, err := os.Create(outFileName)
	if err != nil {
		fmt.Println(err)
		os.Exit(-2)
	}
	//fmt.Printf("Successfully Created `%s`\n", fileName)

	defer firmware.Close()
	paddr := 0

	// Start scanning instructions
	for scanner.Scan() {
		line := scanner.Text()
		if line == "" {
			continue
		}

		fields := strings.Split(line, " ")
		if len(fields) == 0 {
			continue
		}

		// Did the new address increment more than 1?
		naddr, err := StringHexToInt(fields[0])
		if err != nil {
			fmt.Println("oops")
			return
		}

		if naddr > (paddr + 1) {
			// Generate zero padding
			for paddr < naddr-1 {
				outLine := fmt.Sprintf("        self.instructions.append(0x00000000)\n")
				firmware.WriteString(outLine)
				paddr++
			}
		}
		paddr = naddr

		outLine := fmt.Sprintf("        self.instructions.append(0x%s)\n", fields[1])
		firmware.WriteString(outLine)
	}
}

func StringHexToInt(hex string) (value int, err error) {
	hex = strings.Replace(hex, "@", "", 1)

	v, err := strconv.ParseInt(hex, 16, 64)
	if err != nil {
		return 0, err
	}
	value = int(v)

	return value, nil
}
