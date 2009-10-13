all: clean build test

build:
	python build.py
	ant compile
	ant jar

clean:
	-rm -rf build
	-rm CobblerDistro.java
	-rm CobblerProfile.java
	-rm CobblerSystem.java
	-rm CobblerImage.java
	-rm CobblerRepo.java
	ant clean

test:
	# ant test 
	# java -classpath xmlrpc.jar:simple-xmlrpc.jar:simple.jar -jar cobbler4j.jar http://127.0.0.1/cobbler_api
	java -classpath . -jar cobbler4j.jar http://127.0.0.1/cobbler_api
