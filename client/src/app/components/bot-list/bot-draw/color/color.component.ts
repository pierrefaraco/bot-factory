import { Component, EventEmitter, Output, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
@Component({
  selector: 'app-color',
  standalone: true,
  imports: [MatIconModule],
  templateUrl: './color.component.html',
  styleUrl: './color.component.scss'
})
export class ColorComponent {

  @Output() colorChange = new EventEmitter<number>();
  @Output() previousItem = new EventEmitter();
  @Output() nextItem = new EventEmitter();
  @Input() imgAddress: string = "";
  @Input() maxNavPos: number = 12;
  @Input() colors = [
    '#000000',
    '#000000',
    '#000000',
    '#000000',
    '#000000',
    '#000000'
  ]
  @Input() navPos:number = 0;
 


  setColor(color: number) {
    this.colorChange.emit(color);
  }

  previous() {
    if (this.navPos == 0) {
      return;
    }
    this.navPos = this.navPos - 1;
    this.previousItem.emit();
  }
  next() {
    if (this.navPos == this.maxNavPos) {
      return;
    }
    this.navPos = this.navPos + 1;
    this.nextItem.emit();
  }

  isLastItem() {
    return this.navPos == this.maxNavPos
  }

  isFirstItem() {
    return this.navPos == 0
  }

}
