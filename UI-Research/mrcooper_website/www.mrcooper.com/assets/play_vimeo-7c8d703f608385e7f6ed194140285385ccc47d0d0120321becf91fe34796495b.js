(function () {
  window.mrc = window.mrc || {};

  window.mrc.playVimeo = function (iframeId) {
    var iframe = document.querySelector('#' + iframeId);
    var player = new Vimeo.Player(iframe); // eslint-disable-line no-undef
    player.play();
  };
})();
