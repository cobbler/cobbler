<h1>Simple RSS agregator</h1>
<a href="http://www.webdot.cz/lastrss/">
<img src="lastrss_button.gif" alt="" width="88" height="31" border="0">
</a><hr>
<!-- / Heading -->

<?php
/* 
 ======================================================================
 lastRSS usage DEMO 3 - Simple RSS agregator
 ----------------------------------------------------------------------
 This example shows, how to create simple RSS agregator
     - create lastRSS object
    - set transparent cache
    - show a few RSS files at once
 ======================================================================
*/

function ShowOneRSS($url) {
    global $rss;
    if ($rs = $rss->get($url)) {
        echo "<big><b><a href=\"$rs[link]\">$rs[title]</a></b></big><br />\n";
        echo "$rs[description]<br />\n";

            echo "<ul>\n";
            foreach ($rs['items'] as $item) {
                echo "\t<li><a href=\"$item[link]\" title=\"$item[description]\">$item[title]</a></li>\n";
            }
            if ($rs['items_count'] <= 0) { echo "<li>Sorry, no items found in the RSS file :-(</li>"; }
            echo "</ul>\n";
    }
    else {
        echo "Sorry: It's not possible to reach RSS file $url\n<br />";
        // you will probably hide this message in a live version
    }
}

// ===============================================================================

// include lastRSS
include "./rss-parser.php";

// List of RSS URLs
$rss_left = array(
    'http://freshmeat.net/backend/fm.rdf',
    'http://slashdot.org/slashdot.rdf'
);
$rss_right = array(
    'http://www.freshfolder.com/rss.php',
    'http://phpbuilder.com/rss_feed.php'
);

// Create lastRSS object
$rss = new lastRSS;

// Set cache dir and cache time limit (5 seconds)
// (don't forget to chmod cahce dir to 777 to allow writing)
$rss->cache_dir = './temp';
$rss->cache_time = 1200;


// Show all rss files
echo "<table cellpadding=\"10\" border=\"0\"><tr><td width=\"50%\" valign=\"top\">";
foreach ($rss_left as $url) {
    ShowOneRSS($url);
}
echo "</td><td width=\"50%\" valign=\"top\">";
foreach ($rss_right as $url) {
    ShowOneRSS($url);
}
echo "</td></tr></table>";
?>

