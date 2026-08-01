/* global Sentry */
(function(){

    var script=document.createElement("script");

    script.src=
    "https://browser.sentry-cdn.com/10.1.0/bundle.min.js";


    script.onload=function(){

        Sentry.init({

            dsn:"https://a0925cf9dcdc3feae0e225bb50d04fa1@o4511830522265600.ingest.us.sentry.io/4511830661529600",

            environment:"nexora",

            tracesSampleRate:1.0

        });


        console.log(
        "NEXORA SENTRY FRONTEND ACTIVE"
        );


    };


    document.head.appendChild(script);


})();
