$(document).ready(function() {
  $('.tt-hint').addClass('form-control');
  var engine = new Bloodhound({
    datumTokenizer: Bloodhound.tokenizers.obj.whitespace('name'),
    queryTokenizer: Bloodhound.tokenizers.whitespace,
    limit: 10,
    remote: $SCRIPT_ROOT + "/filer_search?q=%QUERY"
  });

  engine.initialize();

  $( "#typeahead" ).typeahead({
    hint: true,
    highlight: true,
    minLength: 2
  },
  {
    name: 'filers',
    displayKey: 'name',
    source: engine.ttAdapter()
  }).on("typeahead:selected", function (event, data, dataset) {
    window.location.href = "/form_four?q=" + encodeURIComponent(data.cik);
  });
});
