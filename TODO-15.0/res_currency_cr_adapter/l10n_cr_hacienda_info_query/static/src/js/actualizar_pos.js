function httpGet(theUrl)
{

    var nombre;
    var identificacion;
    var activity;
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
            document.getElementsByName("name")[0].value = obj.nombre;
            activity = obj.activity;
            nombre = obj.nombre;
            identificacion = parseInt(obj.identification_id);

        }
    }
    xmlhttp.open("GET", theUrl, false);
    xmlhttp.send();
    var result = {'nombre': nombre, 'identificacion': identificacion, 'activity': activity};

    return result

}

      
