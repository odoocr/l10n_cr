function httpGet(theUrl)
{
    if (window.XMLHttpRequest)
    {// code for IE7+, Firefox, Chrome, Opera, Safari
        xmlhttp=new XMLHttpRequest();
    }
    else
    {// code for IE6, IE5
        xmlhttp=new ActiveXObject("Microsoft.XMLHTTP");
    }
    xmlhttp.onreadystatechange=function()
    {
        if (xmlhttp.readyState==4 && xmlhttp.status==200)
        {
            //alert(xmlhttp.responseText)
            var obj = JSON.parse(xmlhttp.responseText);
            document.getElementsByName("name")[0].value = obj.nombre
            document.getElementsByName("identification_id")[0].value = parseInt(obj.identification_id)
        }
    }
    xmlhttp.open("GET", theUrl, false);
    xmlhttp.send();    
}

function obtener_nombre(vat) {
        document.getElementsByName("vat")[0].value = vat
        var host = window.location.host
        var end_point = "http://" + host + "/cedula/" + vat
        httpGet(end_point)
        }


      
