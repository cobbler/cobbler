package org.fedorahosted.cobbler.test;

public class Config {

	/**
	 * CONNECTION CONFIG ENTRIES
	 */

	public static String getUser() {
		return System.getProperty("username");
	}

	public static String getPassword() {
		return System.getProperty("password");
	}

	public static String getHostname() {
		return System.getProperty("hostname");
	}

	public static String getCentosMirror() {
		return System.getProperty("centosMirror");
	}

/*	public static String getHostUrl() {
		return System.getProperty("host");
	}

	public static String getProtocol() {
		return System.getProperty("proto");
	}

	public static String getPath() {
		return System.getProperty("path");
	}
	*/







}
