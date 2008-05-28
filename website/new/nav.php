<?php


  switch ($current_page) {

	case "about":
		echo "<ul id=\"nav\">
  		 <li id=\"active\"><a href=\"index.php\">About</a></li>
   		<li><a href=\"download.php\">Download</a></li>
  		 <li><a href=\"https://fedorahosted.org/projects/cobbler\">Wiki</a></li>
 		</ul>";
		break;
  	case "download":
		echo "<ul id=\"nav\">
   		<li><a href=\"index.php\">About</a></li>
  		 <li id=\"active\"><a href=\"#\">Download</a></li>
  		 <li><a href=\"http://hosted.fedoraproject.org/projects/cobbler/\">Wiki</a></li>
		 </ul>";
		break;
	default:
		echo " <ul id=\"nav\">
  		 <li id=\"active\"><a href=\"index.php\">About</a></li>
  		 <li><a href=\"download.php\">Download</a></li>
  		 <li><a href=\"http://hosted.fedoraproject.org/projects/cobbler/\">Wiki</a></li>
 		</ul>";
		break;

}

?>

