all: build clean jar

build: clean
	python build.py
	ant compile
	ant jar

clean:
	rm Distro.java
	rm Profile.java
	rm System.java
	rm Image.java
	rm Repo.java
	ant clean
