<template>
  <div class="modal" id="termsModal" tabindex="-1" role="dialog" data-backdrop="static">
    <div class="modal-dialog" role="document">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title">{{ $root._('Terms of Use') }}</h5>
        </div>
        <div class="modal-body">
          <p>{{ $root._('Terms of Use Body Text') }}</p>
        </div>
        <div class="modal-footer">
          <button
            type="button"
            class="btn btn-primary"
            @click="closePopup"
            @keyup.enter="closePopup"
            >{{ $root._('Agree and Proceed') }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: "TermsOfUsePopup",
  data: function() {
    return {
      displayPopup: this.sessionStorageDisplayPopupValue ? this.sessionStorageDisplayPopupValue : true
    };
  },
  mounted: function() {
    this.setModalVisibility();
  },
  updated: function() {
    this.setModalVisibility();
  },
  methods: {
    setModalVisibility() {
      this.getDisplayPopupFromSessionStorage();
      if (this.displayPopup) {
        $('#termsModal').modal('show');
      } else {
        this.closePopup();
      }
    },
    closePopup() {
      $('#termsModal').modal('hide');
      this.setPopupDataClosed();
    },
    setPopupDataClosed() {
      window.sessionStorage.setItem(this.sessionStoragePopupKey, false);
      this.displayPopup = false;
    },
    getDisplayPopupFromSessionStorage() {
      if (window.sessionStorage) {
        if (this.sessionStorageDisplayPopupValue !== null) {
          let isTrue = (this.sessionStorageDisplayPopupValue === 'true');
          this.displayPopup = isTrue;
        }
      }
    }
  },
  computed: {
    sessionStoragePopupKey() {
      return 'ukwa-pywb--terms-of-use-popup';
    },
    sessionStorageDisplayPopupValue() {
      return window.sessionStorage.getItem(this.sessionStoragePopupKey);
    }
  }
}
</script>
