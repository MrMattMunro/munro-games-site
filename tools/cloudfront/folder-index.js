// CloudFront viewer-request function on play.munro.games: lets /<game> and /<game>/ serve
// /<game>/index.html. The S3 origin is the REST endpoint, which has no per-folder index.
function handler(event) {
    var request = event.request;
    var uri = request.uri;
    if (uri.endsWith('/')) {
        request.uri = uri + 'index.html';
        return request;
    }
    var last = uri.substring(uri.lastIndexOf('/') + 1);
    if (last.indexOf('.') === -1) {
        return {
            statusCode: 301,
            statusDescription: 'Moved Permanently',
            headers: { location: { value: uri + '/' } }
        };
    }
    return request;
}
