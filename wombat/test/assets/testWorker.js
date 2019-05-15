self.isFetchOverridden = () =>
  self.fetch.toString().includes('rewriteFetchApi');
self.isImportScriptOverridden = () =>
  self.importScripts.toString().includes('rewriteArgs');
self.isAjaxRewritten = () =>
  self.XMLHttpRequest.prototype.open.toString().includes('rewriteURL');
