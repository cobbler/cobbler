var js_growl = new jsGrowl('js_growl');
var run_once = 0
var taskmem = new Array()
var now = new Date()
var page_load = -1

/* show tasks not yet recorded, update task found time in hidden field */

function get_latest_task_info() {

    if (page_load == -1) {
        /* the first time on each page, get events since now - 1 second */
        /* after just track new ones */
        page_load = now.getTime() - 1
    }

    $.getJSON("/cblr/svc/op/tasks/since/" + page_load,
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
               if (state == "complete") {
                    buf = "Task " + name + " is running: " + logmsg
               }
               if (state == "failed") {
                    buf = "Task " + name + " has failed: " + logmsg
               }
               else {
                    buf = name
               }
               show_it = False
               if (taskmem.indexOf(ts) == -1) {
                   show_it = True
                   taskmem[ts] = state
               }
               else {
                   if (taskmem[ts] != state) {
                       show_it = True
                       taskmem[ts] = state
                   }
               }

               if (show_it) {
                   js_growl.addMessage({msg:buf});
               }
          });
        });

        now = new Date()
        last_time = now.getTime()
}

function go_go_gadget() {
    js_growl.addMessage({msg:'Hello'})
    get_latest_task_info()
    setInterval(get_latest_task_info, 10)
    if (page_onload) {
       page_onload()
    }
}


