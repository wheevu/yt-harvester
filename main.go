package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"os"

	"github.com/wheevu/yt-harvester/internal/app"
	"github.com/wheevu/yt-harvester/internal/cli"
)

func main() {
	os.Exit(run())
}

func run() int {
	opts, err := cli.Parse(os.Args[1:])
	if err != nil {
		if errors.Is(err, flag.ErrHelp) {
			fmt.Fprint(os.Stdout, cli.Usage())
			return 0
		}

		fmt.Fprintf(os.Stderr, "Error: %v\n\n", err)
		fmt.Fprint(os.Stderr, cli.Usage())
		return 1
	}

	outputPath, err := app.Run(context.Background(), opts, func(message string) {
		fmt.Fprintln(os.Stdout, message)
	})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Failed to harvest video report: %v\n", err)
		return 1
	}

	fmt.Fprintf(os.Stdout, "Done: %s\n", outputPath)
	return 0
}
