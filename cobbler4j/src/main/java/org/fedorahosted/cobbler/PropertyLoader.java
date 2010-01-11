package org.fedorahosted.cobbler;


import java.io.BufferedReader;
import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class PropertyLoader {

	public void load() throws Exception {
      BufferedReader reader = new BufferedReader(new FileReader(System.getProperty("user.dir")+"/user.properties"));
      Map<String, String> p = new HashMap<String, String>();
      while (true) {
          String line = reader.readLine();
          if (line == null) break;
          if (line.length() == 0 || line.startsWith("#"))
              continue;
          String[] parts = line.split("=", 2);
          if (parts.length < 2) {
              System.err.println("Malformed property: "+line);
              continue;
          }
          parts[1] = replaceVariables(p, parts[1]);
          p.put(parts[0], parts[1]);
          System.setProperty(parts[0], parts[1]);
      }
  }

	/**
     * Replace embedded variables.  These are values that contain previously
     * defined variables.
     */
    private String replaceVariables(Map<String,String> p, String s) {
        int i = 0;
        StringBuilder sb = new StringBuilder();
        Matcher m = pattern.matcher(s);
        while (m.find(i)) {
            String key = m.group(2);
            String value = p.get(key);
            if (value == null)  continue;
            int start = m.start();
            int end = m.end();
            sb.append(s.substring(i, start));
            sb.append(value);
            i = end;
        }
        sb.append(s.substring(i));
        return sb.toString();
    }

    Pattern pattern = Pattern.compile("(\\$\\{)([^}]+)(\\})");

}