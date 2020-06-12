//Viz is a global object and it is created once.
var viz;

$(document).ready(function () {
    var query = "MATCH (n:Word)-[r:connects]-(k) "
        + "WHERE n.pagerank > 90 "
        + "AND k.pagerank > 90 "
        + "AND n.pagerank < 200 "
        + "AND k.pagerank < 200 "
        + "RETURN n,r,k LIMIT 1000";
    draw(query);
});

$("#query").click(function () {
    var start = $("#field1").val();
    var end = $("#field2").val();
    var score = $("#field3").val();
    if (start === "" || end === "" || score === "") {
        alert("Please speficy the ranges and/or score!");
        return;
    }
    // Build the query based on the above values.
    var query = "MATCH (n:Word)-[r:connects]-(k) "
        + "WHERE n.pagerank > " + start + " "
        + "AND k.pagerank > " + start + " "
        + "AND n.pagerank < " + end + " "
        + "AND k.pagerank < " + end + " "
        + "AND r.weight >= " + score + " "
        + "RETURN n,r,k LIMIT 1000";
    viz.renderWithCypher(query);
});

$("#stabilize").click(function () {
    viz.stabilize();
})

$("#textarea").keyup(function (e) {
    var code = e.keyCode ? e.keyCode : e.which;
    if (code === 13) { // Enter key pressed.
        var query = $("#textarea").val().replace(/\r?\n|\r/g, "");
        // Set value back to retain the query 
        // without any newline characters.
        $("#textarea").val(query);
        if (query === ""){
            alert("Please supply a query!");
            return;
        }
        viz.renderWithCypher(query);
        return;
    }
});

function draw(query) {
    // Create a config object for viz.
    var config = {
        container_id: "viz",
        server_url: "bolt://localhost:7687",
        server_user: "neo4j",
        server_password: "123",
        labels: {
            "Word": {
                caption: "key",
                size: "pagerank",
                community: "community"
            },
            "Paper": {
                caption: "title",
                size: "none",
                community: "community"
            },
            "Author": {
                caption: "name",
                size: "none",
                community: "none"
            },
            "Location": {
                caption: "name",
                size: "none",
                community: "none"
            },
            "Institution": {
                caption: "name",
                size: "none",
                community: "none"
            },
            "Laboratory": {
                caption: "name",
                size: "none",
                community: "none"
            }
        },
        relationships: {
            "connects": {
                caption: "weight",
                thickness: "weight"
            },
            "cites": {
                caption: "none",
                thickness: "none"
            },
            "abstract_includes": {
                caption: "none",
                thickness: "none"
            },
            "affiliates_with": {
                caption: "none",
                thickness: "none"
            },
            "is_similar": {
                caption: "score",
                thickness: "score"
            }
        },
        initial_cypher: query
    }
    viz = new NeoVis.default(config);
    viz.render();
    return 
}
