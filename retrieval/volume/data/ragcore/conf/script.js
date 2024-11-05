function processAdd(cmd) {
	// implements org.apache.solr.common.SolrInputDocument
	// https://solr.apache.org/docs/7_1_0/solr-solrj/org/apache/solr/common/SolrInputDocument.html
	var doc = cmd.solrDoc;  

	var language = doc.getFieldValue("language_s");
	var text = doc.getFieldValue("text")
	const prefix = "text_"

	/* set default language
	if (!["en", "de", "hu"].includes(language)) {
		language = "en"
		doc.setFieldValue("language_s", "en")
	}
	*/
	
	doc.setField(prefix + language, text);
	doc.removeField("text")
}

function processDelete(cmd) {
	// no-op
}

function processMergeIndexes(cmd) {
	// no-op
}

function processCommit(cmd) {
	// no-op
}

function processRollback(cmd) {
	// no-op
}

function finish() {
	// no-op
}