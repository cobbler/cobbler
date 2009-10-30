all: clean build test

build:
	python build.py
	ant build

clean:
	-rm -rf build
	-rm Distro.java
	-rm Profile.java
	-rm SystemRecord.java
	-rm Image.java
	-rm Repo.java

test:
	ant test
