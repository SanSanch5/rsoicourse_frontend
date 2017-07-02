function roleRadioClick() {
    var group_block = $("#student-group");
    var tutor_block = $("#student-tutor");
    var group_input = document.getElementById('group');
    if (document.getElementById('student-radio').checked) {
        console.log("Меняется роль на студента");
        group_block.removeClass("hidden");
        tutor_block.removeClass("hidden");
        group_block.addClass("required");
        group_input.required = true;
    } else {
        console.log("Меняется роль на преподавателя");
        group_block.addClass("hidden");
        tutor_block.addClass("hidden");
        group_block.removeClass("required");
        group_input.required = false;
    }
}
