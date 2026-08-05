.PHONY: install build test clean fmt

install:
	go install .

build:
	go build -o yt-harvester .

test:
	go test ./...

clean:
	rm -f yt-harvester
	go clean

fmt:
	go fmt ./...
