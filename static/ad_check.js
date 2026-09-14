(function(){
    var _adNotified = false;
    var _token = '';
    var m = document.cookie.match(/(?:^|;\s*)token=([^;]*)/);
    if (m) _token = m[1];
    if (!_token) {
        var u = new URLSearchParams(window.location.search);
        _token = u.get('token') || '';
    }
    setInterval(function(){
        fetch("/stream_status?token=" + _token)
        .then(function(r){ return r.json(); })
        .then(function(d){
            if (d.ad_pending && !_adNotified) {
                _adNotified = true;
                if (window.Android && Android.showAdOverlay) {
                    Android.showAdOverlay();
                }
            }
            if (!d.ad_pending) {
                _adNotified = false;
            }
        }).catch(function(){});
    }, 2000);
})();
