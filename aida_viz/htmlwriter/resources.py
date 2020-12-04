TEMPLATE = """
<!doctype html>
<html lang="en">
  <head>

    <meta charset="utf-8">
    <title>{{ title }}</title>
    <link
      rel="stylesheet"
      href="./style.css">
  </head>

  <body>
    <div class="card" style="width:100%;float:left;">
      <div class="card-header text-center bg-light-custom">
        {{ document.title }}
      </div>
      <div class="card-body document-details-modal modal-body text-left">
        {{ document.html|safe }}
      </div>
    </div>

    <script>
      (function() {
        var mention = document.getElementById('contextof-{{ document.span }}');
        mention.scrollIntoView({
            'behavior': 'auto',
            'block': 'center',
            'inline': 'center'
        });
      })();
    </script>
  </body>
</html>
"""

STYLE = """
body {
  padding: 2.5%
}

.text-center{
  text-align:center
}

.text-left{
  text-align:left
}

.document-details-modal.modal-body {
  max-height: 80vh;
  overflow-y: auto;
  white-space: pre-wrap;
}

.card {
  position: relative;
  display: -webkit-box;
  display: -ms-flexbox;
  display: flex;
  -webkit-box-orient: vertical;
  -webkit-box-direction: normal;
  -ms-flex-direction: column;
  flex-direction: column;
  min-width: 0;
  word-wrap: break-word;
  background-color: #fff;
  background-clip: border-box;
  border: 1px solid rgba(0, 0, 0, .125);
  border-radius: .25rem;
  width: 100%;
  height: 100%;
  margin: 0 auto;
  float: none;
  margin-bottom: 20px;
}

.card-header {
  padding: .75rem 1.25rem;
  margin-bottom: 0;
  background-color: rgba(0, 0, 0, .03);
  border-bottom: 1px solid rgba(0, 0, 0, .125)
}

.card-body {
  -webkit-box-flex: 1;
  -ms-flex: 1 1 auto;
  flex: 1 1 auto;
  padding: 1.25rem
}

.mention-card-body-context:hover {
  text-decoration: underline;
}

.card-group {
  width: 100%;
  margin: 0 auto; /* Added */
  float: none; /* Added */
  margin-bottom: 10px; /* Added */
}

.bg-light-custom {
  background: #e6e6e6;
}

span.mention.primary-mention {
  background-color: #ffc107
}

span.mention {
  background-color: #FFFF00
}

span.mention-context {
  font-weight: bold
}

ul{
  padding-left: 20px;
}

.table-hover tbody tr:hover td, .table-hover tbody tr:hover th {
  background-color: rgb(66,139,202,0.5) ;
}

:target {
  background-color: #FFFF00;
}
"""
