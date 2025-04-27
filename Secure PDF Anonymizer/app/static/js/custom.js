$(document).ready(function(){
    if (!$.fn.DataTable.isDataTable('#editorTable')) {
        $('#editorTable').DataTable({
            responsive: true,
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
            language: {
                search: "Kayıtları Filtrele:",
                lengthMenu: "_MENU_ giriş göster",
                info: "_START_ - _END_ / _TOTAL_ giriş gösteriliyor",
                paginate: {
                    previous: "Önceki",
                    next: "Sonraki"
                }
            }
        });
    }

    if (!$.fn.DataTable.isDataTable('#reviewerTable')) {
        $('#reviewerTable').DataTable({
            responsive: true,
            dom: 'Bfrtip',
            buttons: ['copy', 'csv', 'excel', 'pdf', 'print'],
            language: {
                search: "Kayıtları Filtrele:",
                lengthMenu: "_MENU_ giriş göster",
                info: "_START_ - _END_ / _TOTAL_ giriş gösteriliyor",
                paginate: {
                    previous: "Önceki",
                    next: "Sonraki"
                }
            }
        });
    }

    if (!$.fn.DataTable.isDataTable('#entitiesTable')) {
        $('#entitiesTable').DataTable({
            responsive: true,
            searching: true,
            paging: true,
            language: {
                search: "Varlık Ara:",
                lengthMenu: "_MENU_ varlık göster",
                info: "_START_ - _END_ / _TOTAL_ varlık gösteriliyor",
                paginate: {
                    previous: "Önceki",
                    next: "Sonraki"
                }
            }
        });
    }
});