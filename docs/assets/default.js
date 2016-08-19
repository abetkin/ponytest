define("analytics", ["require", "exports", "module"], function(require, exports, module) {
(function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
(i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
})(window,document,'script','//www.google-analytics.com/analytics.js','ga');
ga('create', 'UA-49208336-4', 'auto');
ga('send', 'pageview');

});
define('default', ['exports', 'docsearch'], function (exports, _docsearch) {
  'use strict';

  (0, _docsearch)({
    apiKey: 'cf314b2976b27157c82b6f27553497f5',
    indexName: 'flowtype',
    inputSelector: '#algolia-doc-search'
  });
});