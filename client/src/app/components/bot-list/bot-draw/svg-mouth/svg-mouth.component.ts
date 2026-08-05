import { Component, Input ,OnInit } from '@angular/core';
import {AVATAR_COLORS} from '../../../../constants/color.constants'
import { CommonModule } from '@angular/common';

const CSS_CLASS_BACKGROUND = '.background-mouth';
const CSS_CLASS_DRAW = '.draw-mouth';

@Component({
  selector: 'app-svg-mouth',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './svg-mouth.component.html',
  styleUrl: './svg-mouth.component.scss'
})
export class SvgMouthComponent implements OnInit {
 @Input() choosenColorIndice = 0;
  @Input() choosenItemIndice = 0;
  @Input() height:number = 64.0;
  @Input() offset:number = 0;
  choosen_color = AVATAR_COLORS[this.choosenColorIndice];

  svgWidth:number = this.height * 10
  svgHeight:number = this.height;
  high = "0px"
  startLeft = 0
  step:number = - this.svgWidth/ 15.0
  currentPosition: number = 0;// this.choosenItemIndice;

  hatPositions : Array<{ top: string, left: string }> = [];


  ngOnInit(): void {
    this.initPositionsArray()
  }

  initPositionsArray(): void {
    this.svgWidth = this.height * 10
    this.svgHeight = this.height;
    this.step = - this.svgWidth/ 15.0
    this.high = -this.offset + "px"
    this.hatPositions = [
      { top: this.high, left: this.startLeft + 'px' },
      { top: this.high, left: (this.startLeft + this.step) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 2) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 3) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 4) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 5) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 6) + 'px' },
      { top: this.high, left: (-1 + this.step * 7) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 8) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 9) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 10) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 11) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 12) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 13) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 14) + 'px' },
      { top: this.high, left: (this.startLeft + this.step * 15) + 'px' }
    ];

  }
  public updateColor(indice:number): void {
    this.choosenColorIndice = indice;
  }

  getColor(): string {
    this.initPositionsArray()
    return AVATAR_COLORS[this.choosenColorIndice];
  }

  getStyle(): { top: string, left: string } {
    return this.hatPositions[this.choosenItemIndice];
  }
} 