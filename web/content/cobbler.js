var js_growl = new jsGrowl('js_growl');
var run_once = 0
var now = new Date()
var page_load = -1

/* show tasks not yet recorded, update task found time in hidden field */

function get_latest_task_info() {

    if (page_load == -1) {
        /* the first time on each page, get events since now - 1 second */
        /* after just track new ones */
        page_load = (now.getTime() * 1000) - 5
    } else {
        page_load = page_load + 5000
    }

    $.getJSON("/cblr/svc/op/events/since/" + page_load,
        function(data){
          $.each(data, function(i,record){


               var id = record[0];
               var ts = record[1];
               var name = record[2];
               var state = record[3];
               var buf = ""
               var logmsg = " <A HREF=\"/cobbler_web/tasklog/" + id + "\">(log)</A>";
               if (state == "complete") {
                    buf = "Task " + name + " is complete: " + logmsg
               }
               if (state == "running") {
                    buf = "Task " + name + " is running: " + logmsg
               }
               if (state == "failed") {
                    buf = "Task " + name + " has failed: " + logmsg
               }
               else {
                    buf = name
               }

               js_growl.addMessage({msg:buf});
          });
        });

}

function go_go_gadget() {
    get_latest_task_info()
    setInterval(get_latest_task_info, 5000)
    try {
       page_onload()
    } 
    catch (error) {
    }
}


