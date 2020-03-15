let webSocketBridge = null;
let listeningJobs = {};

function issue() {
    const maxRetries  = 1;

    const wsUrl = "ws://" + window.location.host + "/command";
    if (!(webSocketBridge && webSocketBridge.socket && webSocketBridge.socket.readyState == WebSocket.OPEN)) {
        webSocketBridge = new channels.WebSocketBridge({maxRetries: maxRetries});
        webSocketBridge.connect(wsUrl);
        webSocketBridge.listen(function(msg, stream){
            let outputTextarea = $('#output');
            outputTextarea.val(outputTextarea.val() + JSON.stringify(msg) + '\n');
            if ('observe_urls' in msg) {
                let observe_urls = msg['observe_urls'];
                let observe_urls_keys = Object.keys(observe_urls);
                for(var i = 0; i < observe_urls_keys.length; i++) {
                    const key = observe_urls_keys[i];
                    const name = '#observe-' + key + '-output';
                    const ws = new channels.WebSocketBridge({maxRetries: maxRetries});
                    ws.connect("ws://" + window.location.host + observe_urls[key]);
                    ws.listen(function(message, stream){
                        $(name).val($(name).val() + '[' + message['id'] + ':' + key + ']' + message['message'] + '\n');
                        $(name).scrollTop($(name)[0].scrollHeight);
                    });
                    listeningJobs[msg['id'] + ':' + key] = ws;
                }

            } else if('command' in msg && msg['command'] == 'stop') {
                ['normal', 'error'].forEach(function(k){
                    let map_key = msg['id'] + ':' + k;
                    if(map_key in listeningJobs) {
                        listeningJobs[map_key].socket.close(1000, "my", {keepClosed:true});
                    }

                })

            }
        });
         function send_command(ws) {
             const jsonCommand = $('#command').val().trim();
             if (jsonCommand.length > 0) {
                 let callback = function() {
                     ws.send(JSON.parse(jsonCommand));
                 }
                 return callback;
             }
        }
        webSocketBridge.socket.addEventListener('open', send_command(webSocketBridge), {once:true});
    } else {
        const jsonCommand = $('#command').val().trim();
        if (jsonCommand.length > 0) {
            webSocketBridge.send(JSON.parse(jsonCommand));
        }
    }
}
function closeWb(wb){
    if (wb && wb.socket && wb.socket.readyState == WebSocket.OPEN) {
        wb.socket.close(1000, "my", {keepClosed:true});
    }
}

$(function(){

    $(window).one('beforeunload', function() {
        closeWb(webSocketBridge);
        let keys = Object.keys(listeningJobs)
        keys.forEach(function(k){
            closeWb(listeningJobs[k]);
        });
    });

    $('#send-command-btn').on('click', function () {
        issue();
    });

    $('#clear-btn').on('click', function () {
        $('#output').val('');
        $('#observe-output').val('');
    });

});