Architecture
============

The pywb system consists of 3 distinct components: Warcserver, Recorder and Rewriter, which can be run and scaled separately.
The default pywb wayback application uses Warcserver and Rewriter. If recording is enabled, the Recorder is also used.

Additionally, the indexing system is used through all components, and a few command line tools encompass the pywb toolkit.


.. toctree::
   :maxdepth: 2

   warcserver
   recorder
   rewriter

   indexing
   apps

