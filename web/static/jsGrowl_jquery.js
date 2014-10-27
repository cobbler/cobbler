/* jsGrowl jQuery Interface */

var jsGrowlInterface = {
  onload: function(jsg){
    $(window).load( function() {
      jsg.onload();
    });
  },
  insert: function(element,html){
    $(element).append(html);
  },
  fade:function(element,after_finish){
    $("#"+element.id).fadeOut(1000,after_finish);
  },
  appear: function(element){
    $("#"+element.id).fadeIn(250);
  },
  remove: function(element){
     $("#"+element.id).remove();
  },
  fadeAndRemove: function(element,jsg,id){
    var f = function(){
      jsGrowlInterface.remove(element);
      jsg.removeMsg(id);
    };
    jsGrowlInterface.fade(element, f);
  }

};