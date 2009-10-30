package org.fedorahosted.cobbler;

import java.util.List;

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
      List<Distro> distros = (List<Distro>)Finder.getInstance().
										listItems(conn, ObjectType.DISTRO);
		System.out.println(distros.get(0));
  }

}
