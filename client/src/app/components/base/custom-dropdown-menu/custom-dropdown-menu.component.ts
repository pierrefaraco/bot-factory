import { CommonModule } from '@angular/common';
import { Component, Input, ElementRef, AfterViewInit, OnDestroy, Renderer2 } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'app-custom-dropdown-menu',
  standalone: true,
  imports: [ CommonModule, MatIconModule,RouterModule],
  templateUrl: './custom-dropdown-menu.component.html',
  styleUrl: './custom-dropdown-menu.component.css'
})
export class CustomDropDownMenuComponent implements AfterViewInit, OnDestroy {
 @Input() items = []
 @Input() params:any
 @Input() isOpen = false

 // Bootstrap's dropdown.js toggles the `.dropdown-menu.show` class directly
 // (via [data-bs-toggle="dropdown"] on the trigger, see admin.component.html
 // / app.component.html) -- it never goes through Angular's [isOpen] input,
 // so the only reliable way to react to open/close is to watch the class.
 private menuEl: HTMLElement | null = null;
 private toggleEl: HTMLElement | null = null;
 private anchor: Comment | null = null;
 private classObserver: MutationObserver | null = null;
 private readonly reposition = () => this.positionMenu();

 constructor(private el: ElementRef<HTMLElement>, private renderer: Renderer2) {}

 ngAfterViewInit() {
   this.menuEl = this.el.nativeElement.querySelector('.dropdown-menu');
   this.toggleEl = this.el.nativeElement.previousElementSibling as HTMLElement | null;
   if (!this.menuEl) {
     return;
   }

   // Placeholder marking where the menu belongs in the Angular-rendered DOM,
   // so it can be moved back there on close instead of staying parked in
   // <body> (where we relocate it while open, see syncMenuState below).
   this.anchor = this.renderer.createComment('dropdown-menu-anchor');
   this.renderer.insertBefore(this.el.nativeElement, this.anchor, this.menuEl);

   this.classObserver = new MutationObserver(() => this.syncMenuState());
   this.classObserver.observe(this.menuEl, { attributes: true, attributeFilter: ['class'] });
 }

 ngOnDestroy() {
   this.classObserver?.disconnect();
   window.removeEventListener('scroll', this.reposition, true);
   window.removeEventListener('resize', this.reposition);
   // Detach in case it was parked in <body> when the row/component was destroyed.
   this.menuEl?.remove();
 }

 private syncMenuState(): void {
   if (!this.menuEl) {
     return;
   }
   const isShown = this.menuEl.classList.contains('show');

   if (isShown) {
     // Reparenting to <body> is what actually escapes ancestor `overflow:
     // auto/hidden` clipping (e.g. admin.component.scss's `.table-container`)
     // -- position: fixed alone does not, since overflow clipping still
     // applies to fixed-position descendants of a clipping ancestor.
     this.positionMenu();
     document.body.appendChild(this.menuEl);
     window.addEventListener('scroll', this.reposition, true);
     window.addEventListener('resize', this.reposition);
   } else {
     window.removeEventListener('scroll', this.reposition, true);
     window.removeEventListener('resize', this.reposition);
     if (this.anchor && this.menuEl.parentElement === document.body) {
       this.anchor.parentNode?.insertBefore(this.menuEl, this.anchor);
     }
     this.renderer.removeStyle(this.menuEl, 'position');
     this.renderer.removeStyle(this.menuEl, 'top');
     this.renderer.removeStyle(this.menuEl, 'left');
     this.renderer.removeStyle(this.menuEl, 'right');
     this.renderer.removeStyle(this.menuEl, 'margin-top');
   }
 }

 private positionMenu(): void {
   if (!this.menuEl || !this.toggleEl) {
     return;
   }
   const toggleRect = this.toggleEl.getBoundingClientRect();
   const menuRect = this.menuEl.getBoundingClientRect();
   const gap = 8; // matches the 0.5rem margin-top the static CSS used
   const viewportHeight = window.innerHeight;
   const viewportWidth = window.innerWidth;

   const fitsBelow = toggleRect.bottom + gap + menuRect.height <= viewportHeight;
   const top = fitsBelow
     ? toggleRect.bottom + gap
     : Math.max(gap, toggleRect.top - gap - menuRect.height);

   // Right-align under the toggle (matches the old `right: 0` rule), clamped
   // so it never runs off either edge of the viewport.
   let left = toggleRect.right - menuRect.width;
   left = Math.min(Math.max(gap, left), viewportWidth - menuRect.width - gap);

   this.renderer.setStyle(this.menuEl, 'position', 'fixed');
   this.renderer.setStyle(this.menuEl, 'top', `${top}px`);
   this.renderer.setStyle(this.menuEl, 'left', `${left}px`);
   this.renderer.setStyle(this.menuEl, 'right', 'auto');
   this.renderer.setStyle(this.menuEl, 'margin-top', '0');
 }

 get filterUpItems (){
    return this.items.filter(item =>!('down' in item) || !item.down);
  }


  get filterDownItems (){
    return this.items.filter(item =>'down' in item && item.down);
  }

}
