<?php
  $current_page = 'news';
?>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
<meta name="description" content="" />
<meta name="keywords" content="" />
<title>Cobbler</title>

  <link rel="stylesheet" href="css/style.css" type="text/css" media="all" />
</head>

<body>
<div id="wrap">
<?php 
  include("top.html"); 
?>

<div id="main">
<div id="sidebar">
<?php 
  include("nav.php"); 
?>
</div>

<div id="content">

<h2>News</h2>

<?php

require_once('magpierss/rss_fetch.inc');

$url = 'http://cobbler.wordpress.com/feed/';
$rss = fetch_rss($url);

	foreach ($rss->items as $item) {
		$href = $item['link'];
		$title = $item['title'];
		$body = $item['content']['encoded'];
		$author = $item['dc']['creator'];
		$category = $item['category'];
		$comment_url = $item['comments'];
		$raw_timestamp = $item['pubdate'];
		$unixtime = strtotime($raw_timestamp);
		$timestamp = date('g:i A T j F Y', $unixtime);

		echo "<h3>$title</h3>";
		echo "<p>$body</p>";
		echo "<p class=\"metadata\">Posted $timestamp by $author in $category &nbsp;|&nbsp; <a href=$href>Comment on this!</a></p>";
	}
	

?>

</div>
</div>
<div id="footer">
<?php 
  include("footer.html"); 
?>
</div>
</div>
</body>
</html>
