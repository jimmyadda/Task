"use strict";

function newTask(event){
    //clearing form
    document.querySelector("[name='title']").value= "";
    document.querySelector("[name='due']").value= "";
    document.querySelector("[name='reminder']").value= "";
    document.querySelector("[name='created']").value= "";
    document.querySelector("[name='category']").value= "BUG";
    document.querySelector("[name='priority']").value= "1";
    document.querySelector("[name='status']").value= "OPEN";
    document.querySelector("[name='notes']").value= "";
    document.querySelector("[name='assignto']").value= "";
    document.querySelector("[name='id']").value= "";
}


function newFolder(event){
let name = prompt("name of new folder?");
let userid = document.querySelector("[name = 'userid']").value;
    if(name.length > 0){
        let f = new FormData();
        f.append("userid",userid);
        f.append("name",name);
        fetch("/new-folder",{
        "method": "POST",
        "body":f,       
        }).then(response => response.text()).then(data => {
            console.log("new folder reply: ",data);
            location.reload();
        });
    }

}

function newFileUpload(event){
    let taskid = document.querySelector("[name = 'id']").value;
    window.location.href = "/upload";   
}

function newTaskNote(event){
    let taskid = document.querySelector("[name = 'id']").value;
    let userid = document.querySelector("[name = 'userid']").value;
    let my_note = document.querySelector("[name = 'note']").value;
    let folderid = document.querySelector("[name = 'folderid']").value;
    
    let f = new FormData();
    f.append("id",taskid)
    f.append("userid",userid);
    f.append("note",my_note);
    f.append("folderid",folderid);
    fetch("/new-note",{
    "method": "POST",
    "body":f,       
    }).then(response => response.text()).then(data => {
        //console.log("New Note Task reply: ",data);
        location.reload();
    });
   
}
function logout_user(event){
    window.location.href = "/logout";
        }

function Remove_file(event){  
    let folderid = document.querySelector("[name = 'folderid']").value;
    let id = document.querySelector("[name = 'id']").value;
    let userid = document.querySelector("[name = 'userid']").value;
    var $row = $(this).closest("tr");
    console.log($row);
    var file = $row.find(".filenames");
    console.log(file[0]);
    file[0].style.text += ' -Deleting';
    var file_to_delete = file[0].getAttribute("name");
     console.log(file_to_delete)

     if(file_to_delete.length > 0){
        let f = new FormData();
        f.append("id",id)
        f.append("userid",userid);
        f.append("filename",file_to_delete);
        fetch("/delete_file",{
        "method": "POST",
        "body":f,       
        }).then(response => response.text()).then(data => {
            console.log("new folder reply: ",data);
            location.reload();
        });
    }

}



function download_file(event){  
    let id = document.querySelector("[name = 'id']").value;
    let userid = document.querySelector("[name = 'userid']").value;    
    var file = event.target.closest('.filenames');
    var file_to_dowload = file.getAttribute("name");

}


function Remove_folder(event){ 
    const res = confirm("Are you sure you want to delete that project?");
    console.log(res)
    if(res){
    let id = document.querySelector("[name = 'id']").value;
    let userid = document.querySelector("[name = 'userid']").value;
    var $row = $(this).closest("tr");
    console.log($row)
    var folder = $row.find(".folderitem");
    console.log(folder)
    //var folder = event.target.closest('.folderitem');
    var folder_to_delete = folder[0].getAttribute("id");
    var foldername = folder[0].getAttribute("name");
            if(folder_to_delete.length > 0){
                let f = new FormData();
                f.append("userid",userid);
                f.append("folderid",folder_to_delete);
                f.append("foldername",foldername);
                console.log(f)
                fetch("/delete_folder",{
                "method": "DELETE",
                "body":f,       
                }).then(response => response.text()).then(data => {
                    console.log("new folder reply: ",data);
                    location.reload();
                });
            }
    }

}
document.querySelector("#new_task_button").addEventListener("click",newTask);
document.querySelector("#new_folder_button").addEventListener("click",newFolder);
document.querySelector("#logout_button").addEventListener("click",logout_user);


let dowloadfiles = document.querySelectorAll("#openfile");
dowloadfiles.forEach(btn => {
    btn.addEventListener('click',download_file);
});

let removefiles = document.querySelectorAll("#removefile_button");
removefiles.forEach(btn => {
    btn.addEventListener('click',Remove_file);
});

let removefolders = document.querySelectorAll("#removefolder");
removefolders.forEach(btn => {
    btn.addEventListener('click',Remove_folder);
});

document.addEventListener("DOMContentLoaded", () => {
    //set selected folder
    let folders_js = document.getElementsByClassName('folderitem');
    let folderid = document.querySelector("[name = 'folderid']").value;
    if(folderid){
        Array.prototype.forEach.call(folders_js, function(folder) {
            // Do stuff here
            if(folderid == folder.id){
                folder.classList.add("myselectedfolder")
            }
        }); 
    }

  });

//Notes 
const addBtn = document.querySelector('#add');
const textArea = document.querySelector('.text-area textarea');
const notes = document.querySelector('.notes');

// Adding Notes by clocking the Add button.
addBtn.addEventListener('click',(e)=>{
    if(textArea.value === ''){
        alert('Please Enter a note.');
        box.remove();
    }
    newTaskNote();
});