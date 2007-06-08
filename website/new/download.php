<?php
  $current_page = 'download';
?>

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">

<head>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
<meta name="description" content="" />
<meta name="keywords" content="" />
<title>UMP: Update and Management Platform</title>

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

<h2>Download</h2>

<?php
  include('download.html');
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
