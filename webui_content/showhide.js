// Javascript code by Máirín Duffy <duffy@redhat.com>


IMAGE_COLLAPSED_PATH = '/img/list-expand.gif';
IMAGE_EXPANDED_PATH  = '/img/list-collapse.gif';
IMAGE_CHILDLESS_PATH  = '/img/rhn-bullet-parentchannel.gif';

var rowHash = new Array();
var browserType;
var columnsPerRow;

// tip of the Red Hat to Mar Orlygsson for this little IE detection script
var is_ie/*@cc_on = {
   quirksmode : (document.compatMode=="BackCompat"),
   version : parseFloat(navigator.appVersion.match(/MSIE (.+?);/)[1])
}@*/;
browserType = is_ie;

function onLoadStuff(columns) {
  columnsPerRow = columns;
  var channelTable = document.getElementById('channel-list');
  createParentRows(channelTable, rowHash);
  reuniteChildrenWithParents(channelTable, rowHash);
  iconifyChildlessParents(rowHash);
}

function iconifyChildlessParents(rowHash) {
  for (var i in rowHash) {
    if (!rowHash[i].hasChildren && rowHash[i].image) { rowHash[i].image.src = IMAGE_CHILDLESS_PATH; }
  }
}

// called from clicking the show/hide button on individual rows in the page
function toggleRowVisibility(id) {
  if (!rowHash[id]) { return; }
  if (!rowHash[id].hasChildren) { return; }
  rowHash[id].toggleVisibility();
  return;
}

function showAllRows() {
  var row;
  for (var i in rowHash) {
    row = rowHash[i];
    if (!row) { continue; }
    if (!row.hasChildren) { continue; }
    row.show();
  }
  return;
}

function hideAllRows() {
  var row;
  for (var i in rowHash) {
    row = rowHash[i];
    if (!row) { continue; }
    if (!row.hasChildren) { continue; }
    row.hide();
  }
  return;
}

function Row(cells, image) {
  this.cells = new Array();
  for (var i = 0; i < cells.length; i++) { this.cells[i] = cells[i]; }
  this.image = image;
  this.hasChildren = 0;
  this.isHidden = 1; // 1 = hidden; 0 = visible.  all rows are hidden by default

// Row object methods below!
  this.toggleVisibility = function() {
    if (this.isHidden == 1) { this.show(); } 
    else if (this.isHidden == 0) { this.hide(); }
    return;
  }

  this.hide = function hide() {
    this.image.src = IMAGE_COLLAPSED_PATH;
// we start with columnsPerRow, because we want to skip the td cells of the parent tr.
    for (var i = columnsPerRow; i < this.cells.length; i++) {
      this.cells[i].parentNode.style.display = 'none';
      this.cells[i].style.display = 'none';
    }
    this.isHidden = 1;
    return;
  }

  this.show = function() {
    displayType = '';
    this.image.src = IMAGE_EXPANDED_PATH;

    for (var i = 0; i < this.cells.length; i++) {
        this.cells[i].style.display = displayType;
        this.cells[i].parentNode.style.display = displayType; 
    }
    this.isHidden = 0;
    return;
  }
}

function createParentRows(channelTable, rowHash) {
  for (var i = 0; i < channelTable.rows.length; i++) {
    tableRowNode = channelTable.rows[i];
    if (isParentRowNode(tableRowNode)) {
      if (!tableRowNode.id) { continue; }
      id = tableRowNode.id;
      var cells = tableRowNode.cells;
      var image = findRowImageFromCells(cells, id)
      if (!image) { continue; }
      rowHash[id] = new Row(cells, image);
    }
  }
  return;
}

function reuniteChildrenWithParents(channelTable, rowHash) {
  var parentNode;
  var childId;
  var tableChildRowNode;
  for (var i = 0; i < channelTable.rows.length; i++) {
    tableChildRowNode = channelTable.rows[i];
// when we find a parent, set it as parent for the children after it
    if (isParentRowNode(tableChildRowNode) && tableChildRowNode.id) {
      parentNode = tableChildRowNode;
      continue; 
    }
    if (!parentNode) { continue; }

    // it its not a child node we bail here
    if (!isChildRowNode(tableChildRowNode)) { continue; }
    // FIXME: chceck child id against parent id
    if (!rowHash[parentNode.id]) { /*alert('bailing, cant find parent in hash');*/ continue; }
    for (var j = 0; j < tableChildRowNode.cells.length; j++) {
      rowHash[parentNode.id].cells.push(tableChildRowNode.cells[j]);
      rowHash[parentNode.id].hasChildren = 1;
    }
  }
  return;
}


function getNodeTagName(node) {
  var tagName;
  var nodeId;
  tagName = new String(node.tagName);
  return tagName.toLowerCase();
}

function isParentRowNode(node) {
  var nodeInLowercase = getNodeTagName(node);
  if (nodeInLowercase != 'tr') { return 0; }
  nodeId = node.id;
  if ((nodeId.indexOf('id')) && !(nodeId.indexOf('child'))) { return 0; }
  return 1;
}

function isChildRowNode(node) {
  var nodeInLowercase = getNodeTagName(node);
  var nodeId;
  if (nodeInLowercase != 'tr') { return 0; }
  nodeId = node.id;
  if (nodeId.indexOf('child')) { return 0; }
  return 1;
}


function findRowImageFromCells(cells, id) {
  var imageId = id + '-image';
  var childNodes; // first level child
  var grandchildNodes; // second level child
  for (var i = 0; i < cells.length; i++) {
    childNodes = null;
    grandchildNodes = null;
    
    if (!cells[i].hasChildNodes()) { continue; }
    
    childNodes = cells[i].childNodes;

    for (var j = 0; j < childNodes.length; j++) {
      if (!childNodes[j].hasChildNodes()) { continue; }
      if (getNodeTagName(childNodes[j]) != 'a') { continue; }
      grandchildNodes = childNodes[j].childNodes;
      
      for (var k = 0; k < grandchildNodes.length; k++) {
        if (grandchildNodes[k].name != imageId) { continue; }
        if (grandchildNodes[k].nodeName == 'IMG' || grandchildNodes[k].nodeName == 'img') { return grandchildNodes[k]; }
      }
    }
  }
  return null;
}
