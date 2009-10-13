all: clean build test

build:
	python build.py
	ant build

clean:
	-rm -rf build
	-rm CobblerDistro.java
	-rm CobblerProfile.java
	-rm CobblerSystem.java
	-rm CobblerImage.java
	-rm CobblerRepo.java

test:
	ant test
