<div id="feed">
<p>Below are the latest 3 message subjects from the <a href="https://www.redhat.com/mailman/listinfo/et-mgmt-tools">et-mgmt-tools list</a>:</p>
<ul>
<?php

require_once('magpierss/rss_fetch.inc');

$url = 'http://rss.gmane.org/gmane.linux.redhat.et-mgmt-tools';
$rss = fetch_rss($url);

	for ($i = 0; $i < 3; $i++) 
	{
		$item_array = $rss->items;
                $item = $item_array[$i];
		$href = $item['link'];
		$title = $item['title'];
		$body = $item['description'];
		$author = $item['dc']['creator'];
		$raw_timestamp = $item['dc']['date'];
		$unixtime = strtotime($raw_timestamp);
		$timestamp = date('g:i A T j F Y', $unixtime);

		echo "<li><a href=$href>$title</a></li>";
	}
	

?>
</ul>
<p>
[ <a href="https://www.redhat.com/archives/et-mgmt-tools/">View More ...</a> ]</p>
</div>
