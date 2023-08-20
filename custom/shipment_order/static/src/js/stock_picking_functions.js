
$(document).ready(function() {
    setTimeout(initQrField,1000);
    function initQrField(){
        if($("#qr_code_data").length > 0){
            if(!$._data($("#qr_code_data")[0], "events")){
                $("#qr_code_data").change( function() {
                    $("#qr_code_data").focus();
                    $("#qr_code_data").select();
                });
                $("#qr_code_data").click(function() {
                    $("#qr_code_data").focus();
                    $("#qr_code_data").select();
                });
            } else{
                if(!$._data($("#qr_code_data")[0], "events").change){
                    $("#qr_code_data").change( function() {
                        $("#qr_code_data").focus();
                        $("#qr_code_data").select();
                    });
                }
                if(!$._data($("#qr_code_data")[0], "events").click){
                    $("#qr_code_data").click(function() {
                        $("#qr_code_data").focus();
                        $("#qr_code_data").select();
                    });
                }
            }
        } 
        setTimeout(initQrField,1000)
    }
});

