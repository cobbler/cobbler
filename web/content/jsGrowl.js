/*  jsGrowl - JavaScript Messaging System, version 1.6.0.3
 *  (c) 2009 Rodrigo DeJuana
 *
 *  jsGrowl is freely distributable under the terms of the BSD license.
 *
 *--------------------------------------------------------------------------*/

function jsGrowlMsg(msg, id) {
  this.initialize(msg, id);
}
//var jsGrowlMsg = Class.create();
jsGrowlMsg.prototype = {
  timeout: 5000,
  hover_timeout: 2000,
  id: null,
  title: null,
  msg: null,
  top: -1000,
  right: -1000,
  element: null,
  timeout_id: 0,
  icon_src: null,
  click_callback: null,
  close_callback: null,
  initialize: function(msg, id){
    this.msg = msg.msg;
    this.title = msg.title;
    this.icon_src = msg.icon;
    this.click_callback = msg.click_callback;
    this.close_callback = msg.close_callback;
    this.sticky = msg.sticky;
    this.id = id;
  },
  html: function(jsg){
    var icon_html = this.icon_src ? '<img src="'+this.icon_src+'" class="jsg_icon">' : '';
    var click_html = this.click_callback ? ' onclick="'+jsg+'.clickMsg('+this.id+');" ' : '';
    var click_css = this.click_callback ? ' class="jsg_clickable" ' : '';
    var title_html = this.title ? '<div class="jsg_title">'+this.title+'</div>' : '';
    return '<table id="growl_flash_msg_'+this.id+'" class="jsgrowl_msg_container"'+
      ' onmouseover="'+jsg+'.overMsg('+this.id+');"'+
      ' onmouseout="'+jsg+'.outMsg('+this.id+');"'+ click_html +
      ' style="right:'+this.right+'px;top:'+this.top+'px;"><tbody '+click_css+'>' +
      '<tr><td class="jsg_corner jsg_tl"></td><td class="jsg_middle"></td><td class="jsg_corner jsg_tr"></td></tr>'+
      '<tr><td class="jsg_side jsg_ml"></td><td class="jsg_body"><div class="jsg_body_container">'+
        '<div id="growl_flash_close_icon_'+this.id+'" title="Close Message" class="jsg_close" '+
        ' onclick="'+jsg+'.closeMsg('+this.id+')"></div>'+
        title_html + icon_html + 
        '<div class="jsg_msg">'+this.msg+'</div>'+
      '</div></td><td class="jsg_side jsg_mr"></tr>'+
      '<tr><td class="jsg_corner jsg_bl"></td><td class="jsg_middle jsg_mb"></td><td class="jsg_corner jsg_br"></td></tr>'+
      '</tbody></table>';
  },
  setElement: function(){
    if (!(this.element)){
      this.element =  document.getElementById('growl_flash_msg_' + this.id);
      if (!(this.element)){
        return false;
      }
    }
    return true;
  },
  height: function(){
    if (this.setElement()){
      return this.element.offsetHeight;
    }else{
      return 75;
    }
  },
  show: function(){
    if (this.setElement()){
      this.element.show();
    }
  },
  hide: function(){
    if (this.setElement()){
      this.element.style.display = 'none';//hide();
    }
  },
  appear: function(){
    jsGrowlInterface.appear(this.element);
  },
  fade: function(jsg,timeout){
    if ( this.sticky ){
      return;
    }
    timeout = timeout > 0 ? timeout : this.timeout;
    var e = this.element;
    var id = this.id;
    var f = function(){
      jsGrowlInterface.fadeAndRemove(e,jsg,id);
    };
    this.timeout_id = setTimeout(f,timeout);
  },
  removeMsg: function(){
    jsGrowlInterface.remove(this.element);
    if ( this.close_callback ){
      this.close_callback();
    }
  },
  onOver: function(){
    clearTimeout(this.timeout_id);
  },
  onOut: function(jsg){
    this.fade(jsg,this.hover_timeout);
  },
  setTop: function(top){
    this.top = top;
    this.element.style.top = top+'px';
  },
  setRight: function(right){
    this.right = right;
    this.element.style.right = right+'px';
  },
  click:function(){
    this.click_callback();
  }
};

function jsGrowl(name,opts) {
  this.initialize(name,opts);
}
//var jsGrowl = Class.create();
jsGrowl.prototype = {
  start_top: 10,
  start_right: 10,
  gap: 10,
  table_width: 300,
  top: 0,
  right: 10,
  width: 0,
  height: 0,
  msg_id: 0,
  messages: {},
  order: [],
  queue: [],
  loaded: false,
  showing: false,
  name: '',
  msg_container: '',
  initialize: function(name,opts){
    opts = opts ? opts : {};
    if ( name ){
      this.name = name;
    }else{
      alert('The variable name is required.  I need this for when I write out the message, the message message can fire the correct events.');
    }
    this.msg_container = opts.msg_container ? opts.msg_container : 'jsGrowl';
    var jsg = this;
    jsGrowlInterface.onload(jsg);
  },
  onload: function(){
    this.msg_container =  document.getElementById(this.msg_container);
    if ( !this.msg_container ){
      //alert('I need a div on your page with the id "jsGrowl" or I will not work.');
    }
    this.loaded = true;
    this.height = (typeof window.innerHeight != 'undefined' ? window.innerHeight : document.documentElement.clientHeight);
    this.width = (typeof window.innerWidth != 'undefined' ? window.innerWidth : document.documentElement.clientWidth);
    this.showMessage();
  },
  addMessage: function(msg) {
    this.queue.push(msg);
    if ( this.loaded && !this.showing ){
      this.showMessage();
    }
  },
  showMessage: function(){
    if ( !this.loaded ){
      return;
    }
    this.showing = true;
    var msg = this.queue.shift();
    if (!msg){
      this.showing = false;
      return;
    }
    var jsg_msg = new jsGrowlMsg(msg, this.msg_id++);
    var jsg = this;

    //this.msg_container.insert(jsg_msg.html(jsg.name));
    jsGrowlInterface.insert(this.msg_container, jsg_msg.html(jsg.name))
    jsg_msg.setElement();
    var insert = this.setLocation(jsg_msg);

    jsg_msg.appear();
    jsg_msg.fade(jsg);

    this.messages[jsg_msg.id] = jsg_msg ;
    if (insert){
      this.order.unshift( jsg_msg.id );
    }else{
      this.order.push( jsg_msg.id );
    }

    var f = function(){ jsg.showMessage(); };
    setTimeout(f,250);
  },
  setLocation: function(msg){
    var insert = this.insertMessage(msg);
    var top = 0;
    var right = 0;
    if (insert){
      top = this.gap;
      right = this.gap;
    }else{
      top = this.top + this.gap;
      right = this.right;
      if (top+msg.height() > this.height){
        right = right + this.table_width + this.gap;
        top = this.gap;
      }
    }

    this.top = top + msg.height();
    this.right = right;

    msg.hide();
    msg.setTop(top);
    msg.setRight(right);
    return insert;
  },
  insertMessage: function(msg){
    for( var i = 0, l = this.order.length; i < l; i++){
      var old_msg = this.messages[this.order[i]];
      if (old_msg){
        return (msg.height()+this.gap) < old_msg.top;
      }
    }
    this.top = 0;
    this.right = 10;
    return false;
  },
  removeMsg: function(id){
    var order = this.order;
    delete this.messages[id];
    var i,l;
    for( i = 0,l = order.length; i < l; i++){
      if (order[i] == id){
        break;
      }
    }
    order.splice(i,1);
    this.order = order;
  },
  overMsg: function(id){
    if (this.messages[id]){
      this.messages[id].onOver();
    }
  },
  outMsg: function(id){
    var jsg = this;
    if (jsg.messages[id]){
      jsg.messages[id].onOut(jsg);
    }
  },
  closeMsg: function(id){
    var jsg = this;
    if (jsg.messages[id]){
      jsg.messages[id].removeMsg();
      jsg.removeMsg(id);
    }
  },
  clickMsg: function(id){
    var jsg = this;
    if (jsg.messages[id]){
      jsg.messages[id].click();
    }
  }
};