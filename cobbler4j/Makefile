all: build clean jar

build: clean
	python build.py
	ant compile
	ant jar

clean:
	-(rm *.java)
	ant clean
