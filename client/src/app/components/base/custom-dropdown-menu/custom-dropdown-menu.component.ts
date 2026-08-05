import { CommonModule } from '@angular/common';
import { Component, Input, ElementRef, AfterViewInit, HostListener } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-custom-dropdown-menu',
  standalone: true,
  imports: [ CommonModule, MatIconModule,RouterModule],
  templateUrl: './custom-dropdown-menu.component.html',
  styleUrl: './custom-dropdown-menu.component.css'
})
export class CustomDropDownMenuComponent implements AfterViewInit {
 @Input() items = []
 @Input() params:any
 @Input() isOpen = false
 
 constructor(private el: ElementRef) {}
 
 ngAfterViewInit() {
   // Setup dropdown positioning
   const dropdown = this.el.nativeElement.querySelector('.dropdown-menu');
   if (dropdown) {
     dropdown.style.position = 'absolute';
   }
 } 

 get filterUpItems (){    
    return this.items.filter(item =>!('down' in item) || !item.down);
  }


  get filterDownItems (){    
    return this.items.filter(item =>'down' in item && item.down);
  }

}
