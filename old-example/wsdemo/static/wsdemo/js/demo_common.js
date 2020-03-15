let webSocketBridge = null;
let listeningJobs = {};

function issue() {
    const maxRetries  = 1;

    const wsUrl = "ws://" + window.location.host + "/command";
    if (!(webSocketBridge && webSocketBridge.socket && webSocketBridge.socket.readyState == WebSocket.OPEN)) {
        webSocketBridge = new channels.WebSocketBridge({maxRetries: maxRetries});
        webSocketBridge.connect(wsUrl);
        webSocketBridge.listen();

        webSocketBridge.demultiplex('normal', function(message, stream){
            if('command' in message) {
                $('#output').val(JSON.stringify(message));
            } else {
                $('#observe-output').val($('#observe-output').val() + '[' + message['id'] + ':normal]' + message['message'] + '\n');
                $('#observe-output').scrollTop($('#observe-output')[0].scrollHeight);
            }
        });
        webSocketBridge.demultiplex('error', function(message, stream){
            $('#observe-error-output').val($('#observe-error-output').val() + '[' + message['id'] + ':error]' + message['message'] + '\n');
            $('#observe-error-output').scrollTop($('#observe-error-output')[0].scrollHeight);

         });
         function send_command(ws) {
             const jsonCommand = $('#command').val().trim();
             if (jsonCommand.length > 0) {
                 let callback = function() {
                     ws.stream('normal').send(JSON.parse(jsonCommand));
                 }
                 return callback;
             }
        }
        webSocketBridge.socket.addEventListener('open', send_command(webSocketBridge), {once:true});
    } else {
        const jsonCommand = $('#command').val().trim();
        if (jsonCommand.length > 0) {
            webSocketBridge.stream('normal').send(JSON.parse(jsonCommand));
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