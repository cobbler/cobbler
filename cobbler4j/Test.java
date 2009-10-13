package org.fedorahosted.cobbler;

public class Test {

  public static final String user = "testing";
  public static final String pass = "testing";
  
  public static void main(String[] args) {
  
      if (args.length < 1) {
          throw new RuntimeException("API endpoint required");
      }
      String endPoint = args[0];
      System.out.println("Running cobbler4j tests against " + endPoint);
      CobblerConnection conn = new CobblerConnection(endPoint,user,pass);
      CobblerDistro distro = new CobblerDistro(conn);
      System.out.println(distro.toString());

  }

}
