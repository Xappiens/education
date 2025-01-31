frappe.ui.form.on("Course Schedule", {
    refresh: function(frm) {
        if (!frm.doc.__islocal) {
            frm.add_custom_button(__("Mark Attendance"), function() {
                frappe.route_options = {
                    based_on: "Course Schedule",
                    course_schedule: frm.doc.name
                }
                frappe.set_route("Form", "Student Attendance Tool");
            });
        }
        // Eliminar dependencia de student_group
        // if (frm.doc.student_group) {
        //     frm.events.get_instructors(frm);
        // }
    },

    onload: (frm) => {
        // Eliminar configuración de consulta para instructor
        // frm.set_query('instructor', () => {
        //     if (frm.instructors.length) {
        //         return {
        //             'filters':{
        //                 'instructor_name': ["in", frm.instructors]
        //             }
        //         };
        //     }
        //     else
        //         return;
        // });

        // Eliminar configuración de consulta para course basada en program
        // frm.set_query('course', function() {
        //     return {
        //         query: 'education.education.doctype.program_enrollment.program_enrollment.get_program_courses',
        //         filters: {
        //             'program': frm.doc.program
        //         }
        //     };
        // });
    },

    // Eliminar evento para student_group
    // student_group: (frm) => {
    //     frm.events.get_instructors(frm);
    // },

    // Eliminar función get_instructors
    // get_instructors: (frm) => {
    //     frm.instructors = [];
    //     frappe.call({
    //         method: 'education.education.api.get_instructors',
    //         args: {
    //             "student_group": frm.doc.student_group
    //         },
    //         callback: function(data) {
    //             frm.instructors = data.message
    //         }
    //     })
    // }
});
