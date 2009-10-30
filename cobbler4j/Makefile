all: clean build test

build:
	python build.py
	ant build

clean:
	-rm -rf build
	-rm src/org/fedorahosted/cobbler/Distro.java
	-rm src/org/fedorahosted/cobbler/Profile.java
	-rm src/org/fedorahosted/cobbler/SystemRecord.java
	-rm src/org/fedorahosted/cobbler/Image.java
	-rm src/org/fedorahosted/cobbler/Repo.java
	-rm cobbler4j.jar

test:
	ant test
